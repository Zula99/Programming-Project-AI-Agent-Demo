- Got to make only good logs show during a crawl

- Need to make the log box:
    - Bigger **DONE**
    - scroll on **DONE**
    - Let all logs show, uncap how far up you can scroll **DONE**
    - Add a search function into the box (OPTIONAL) **DONE**

- Add Stop crawl button functionality. **DONE**

# Add a description of what each milestone does.

- @PLAN.md Add a box that takes text of a target site they want to proxy and a button to launch the proxy, add a drop down of previously indexed files we want the proxy to use in the search API. 

- Start Planning the AI PROMPT EDITOR page 
    - See if we can edit 'backend' from UI
    - if we can reliably, plan out how the backend will look for this feature, explore possible paths of execution
    - Find out what's going to have to change architectually (if it doesn't, nice)WR
    - If it's not a hard thing to implement, Offload to someone else

- Refactor code base to make it look cleaner:
    - make a better codebase structure.
    - Crawler_utils.py is 1200+ lines of code, bad practice.  **DONE**

- file size opensearch_integration.py and proxy_server.py is too big, needs to be refactored. 
