# FastAPI Crawler Automation Backend

This repository contains a basic FastAPI backend server designed to simulate and manage web crawling operations. It provides REST API endpoints to initiate crawls, monitor their status, and retrieve results.

---

## 🚀 Getting Started

Follow these steps to set up and run the backend server on your local machine.


### Setup Instructions

1.  **Navigate to the project directory**:
    Open your terminal and go to the directory where your `main.py` file is located:

    ```bash
    cd ~/Programming-Project-AI-Agent-Demo/ai-agent-demo-factory-backend
    ```

2.  **Install Dependencies**:

    ```bash
    pip install fastapi uvicorn pydantic
    ```

---

## ▶️ Running the Server

Once setup is complete, you can start the FastAPI server.

1.  **Run the Uvicorn server**:

    ```bash
    uvicorn main:app --reload --port 5000
    ```

    You should see output similar to this, indicating the server is running:

    ```
    INFO:     Uvicorn running on [http://127.0.0.1:5000](http://127.0.0.1:5000) (Press CTRL+C to quit)
    ```

---

## 📞 API Endpoints

The server exposes the following REST API endpoints:

### 1. Initiate a New Crawl

* **Endpoint**: `/crawl`
* **Method**: `POST`
* **Description**: Starts a new simulated web crawl in the background. Returns a unique `run_id` to track the crawl.
* **Request Body** (`application/json`):
    ```json
    {
      "target_url": "string"
    }
    ```
* **Example `curl` Command**:
    ```bash
    curl -X POST "[http://127.0.0.1:5000/crawl](http://127.0.0.1:5000/crawl)" \
         -H "Content-Type: application/json" \
         -d '{"target_url": "[https://example.com](https://example.com)"}'
    ```
* **Example Success Response (Status: 202 Accepted)**:
    ```json
    {
      "message": "Crawl initiated successfully",
      "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "status": "pending"
    }
    ```
    *Remember to copy the `run_id` from the response.*

### 2. Check Crawl Status

* **Endpoint**: `/status/{run_id}`
* **Method**: `GET`
* **Description**: Retrieves the current status and progress of a specific crawl run.
* **Path Parameters**:
    * `run_id` (string): The unique ID of the crawl run (obtained from the `/crawl` endpoint).
* **Example `curl` Command**:
    ```bash
    curl -X GET "[http://127.0.0.1:5000/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890](http://127.0.0.1:5000/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890)"
    ```
    *Replace the `run_id` with your actual crawl ID.*
* **Example Responses**:
    * **During crawl**:
        ```json
        {
          "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
          "target_url": "[https://example.com](https://example.com)",
          "status": "running",
          "progress": 50,
          "started_at": 1723724000.0,
          "num_pages_indexed": 5,
          "error_message": null
        }
        ```
    * **After completion**:
        ```json
        {
          "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
          "target_url": "[https://example.com](https://example.com)",
          "status": "complete",
          "progress": 100,
          "started_at": 1723724000.0,
          "num_pages_indexed": 10,
          "error_message": null
        }
        ```
    * **Not Found (Status: 404 Not Found)**: If `run_id` does not exist.
        ```json
        {"detail": "Crawl run not found"}
        ```

### 3. Get Crawl Results

* **Endpoint**: `/results/{run_id}`
* **Method**: `GET`
* **Description**: Retrieves the list of simulated indexed pages for a specific crawl run.
* **Path Parameters**:
    * `run_id` (string): The unique ID of the crawl run.
* **Example `curl` Command**:
    ```bash
    curl -X GET "[http://127.0.0.1:5000/results/a1b2c3d4-e5f6-7890-abcd-ef1234567890](http://127.0.0.1:5000/results/a1b2c3d4-e5f6-7890-abcd-ef1234567890)"
    ```
    *Replace the `run_id` with your actual crawl ID.*
* **Example Success Response (Status: 200 OK)**:
    ```json
    [
      {
        "id": "1",
        "path": "/",
        "title": "Home Page",
        "type": "html",
        "size": 18322
      },
      {
        "id": "2",
        "path": "/products",
        "title": "Our Products",
        "type": "html",
        "size": 25101
      }
      // ... more PageRow objects
    ]
    ```
* **Not Ready/Conflict (Status: 409 Conflict)**: If the crawl is still pending or has failed without results.
    ```json
    {"detail": "Crawl not yet complete or results not available"}
    ```
* **Not Found (Status: 404 Not Found)**: If `run_id` does not exist.
    ```json
    {"detail": "Crawl run not found"}
    ```

---

## 🌐 Interactive API Documentation

While the server is running, you can access the automatically generated interactive API documentation (Swagger UI) in your web browser:

* Open: `http://127.0.0.1:5000/docs`

This interface allows you to explore the endpoints, view their expected request/response schemas, and even send test requests directly from your browser.