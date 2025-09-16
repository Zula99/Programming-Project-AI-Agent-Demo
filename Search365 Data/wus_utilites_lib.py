import requests
import hashlib
import json
from datetime import datetime
from pytz import timezone
import requests
import glob
import spacy
import time
import os
from dotenv import load_dotenv
import base64
import binascii
from jwcrypto import jwk, jwt
from urllib.parse import urlparse


headers = {
        'accept': 'text/plain',
        'Content-Type': 'application/json-patch+json',
        'x-userid': 'auto-test'
    }

class WusUtilities:
    @staticmethod
    def create_doc_id(keyword1, keyword2):
        hash_object = hashlib.sha512((keyword1 + keyword2).encode())
        hex_dig = hash_object.hexdigest()
        return hex_dig

    @staticmethod
    def category_extractor(url:str):
        parsed_url = urlparse(url)
        url_path = parsed_url.path
        path_parts = url_path.strip('/').split('/')
        path_parts = [word for word in path_parts if len(word) > 2]
        print(path_parts)
        if len(path_parts) > 2:
            category_name = path_parts[0]
            category_name = category_name.replace("-", " ")
            category_name = category_name.replace("_", " ")
            return category_name.title()
        elif len(path_parts) == 1:
            category_name = path_parts[0]
            category_name = category_name.replace("-", " ")
            category_name = category_name.replace("_", " ")
            return category_name.title()
        else:
            domain = parsed_url.netloc
            if domain:
                return domain.split('.')[0]
            else:
                return ""

    @staticmethod
    def flat_array(list, spaceing=" "):
        flat_text = (spaceing).join(list)
        return flat_text

class FastLinksLib:

    @staticmethod
    def get_category_id(category_name, api_url):
        body = {
            "query": category_name
        }
        response = requests.post(api_url + "fastLinks/search", headers=headers, json=body)
        data = response.json()
        return data["body"]["result"][0]["id"]

class NavigationLib:
    def get_nav_doc_id(self, nav_name, api_url):
        search_body = {
                          "query": nav_name,
                          "profile": "navigation_test"
                        }
        response = requests.post(api_url + "navigations/search", headers=headers, json=search_body)
        data = response.json()
        doc_id = data["body"]["result"][0]["id"]
        return doc_id

class Search365Lib:
    def __init__(self, env_name_path):
        load_dotenv(dotenv_path=env_name_path, override=True)
        self.tenant_id = os.getenv("APPLICATION_TENANT_ID")
        self.client_id = os.getenv("APPLICATION_CLIENT_ID")
        self.cert_thumbprint = os.getenv("CERT_THUMBPRINT")
        self.private_key_file_path = os.getenv("PRIVATE_KEY_FILE_PATH")
        self.public_key_file_path = os.getenv("PUBLIC_KEY_FILE_PATH")

    @staticmethod
    def get_edm_datetimeoffset(time_zone='UTC'):
        datetime_with_tz = datetime.now(timezone(time_zone))  # Get current time with timezone
        edm_datetimeoffset = datetime_with_tz.isoformat(timespec='milliseconds')  # Format time using ISO 8601
        return edm_datetimeoffset

    @staticmethod
    def create_file_name(title):
        if title is None:  # Check if title is None
            title = "untitled_document"
        file_name = title.replace(" ", "_").replace("’", "").replace("/","_").replace("|","_").replace("&","_").replace("%","_").replace(",","_").replace("?","").replace("'","").replace("-","").replace("(","").replace(")","").replace("__","_").replace("_-_","_").replace(":","")
        file_name = file_name.replace("__","_").replace("_-_","_")
        file_name = file_name.strip("_")
        return file_name

    @staticmethod
    def list_files_in_directory(directory_path):
        try:
            files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]
            return files
        except Exception as e:
            raise e

    @staticmethod
    def check_url_code(url):
        response = requests.get(url)
        status_code = response.status_code
        return status_code

    @staticmethod
    def read_text_file_to_list(file_path):
        with open(file_path, 'r') as f:
            lines = f.readlines()

        lines = [line.strip() for line in lines]
        return lines

    @staticmethod
    def write_json(json_data, file_name="data_backup.json", backup_path="data_2024/"):
        with open(backup_path+file_name, "w") as outfile:
            json.dump(json_data, outfile, indent=4)

    @staticmethod
    def check_doc_attribute(search_agent, doc_url, attribute_name):
        docs_list = []
        result = search_agent.keyword_search(doc_url, request_search_mode="all", request_search_fields=["url"], request_search_filter="url eq '"+doc_url+"'")
        for doc in result:
            docs_list.append([doc_url, doc.get(attribute_name)])
        return docs_list

    @staticmethod
    def export_file(df, dir_path, base_filename, columns):
        try:
            save_path = "{}/{}*.csv".format(dir_path ,base_filename)
            if len(df) > 0:
                file_list = glob.glob(save_path)
                if not file_list:
                    last_file_number = 0
                else:
                    file_numbers = [int(file.split('_')[-1].split('.')[0]) for file in file_list]
                    last_file_number = max(file_numbers)

                next_file_number = last_file_number + 1
                output_file_path = save_path
                df.to_csv(output_file_path, index=False, columns=columns, sep=',', escapechar='\\')
        except Exception as e:
            print(str(e))

    @staticmethod
    def save_json_data(json_data, filename, save_path):
        os.makedirs(save_path, exist_ok=True)
        with open("{}/{}.json".format(save_path, filename), 'w') as f:
            json.dump(json_data, f, default=int, indent=4)

    @staticmethod
    def extract_entity_info(doc):
        nlp = spacy.load("en_core_web_lg")
        nlp_doc = nlp(doc)
        return [(X.text, X.label_) for X in nlp_doc.ents]

    # Create token Start
    @staticmethod
    def get_current_timestamp():
        ts = time.time()
        return ts

    @staticmethod
    def gen_base64_encode(cert_thumbprint):
        byte_string = binascii.unhexlify(cert_thumbprint)
        base64_string = base64.b64encode(byte_string)
        base64_string = base64_string.decode('utf-8')
        return base64_string

    @staticmethod
    def generate_key(self):
        with open(self.private_key_file_path, 'rb') as file:
            private_key = file.read()

        with open(self.private_key_file_path, 'rb') as file:
            public_cert = file.read()

        cert = public_cert + private_key

        key = jwk.JWK.from_pem(cert)
        return key

    def get_client_assertion(self):
        header = {
            "typ": "JWT",
            "x5t": self.gen_base64_encode(self.cert_thumbprint),
            "alg": "RS256"
        }
        payload = {
            "aud": "https://login.microsoftonline.com/{}/oauth2/v2.0/token".format(self.tenant_id),
            # "exp": get_timestamp(2024, 5, 23),
            "exp": self.get_current_timestamp(),
            "iss": self.client_id,
            "jti": "589236252556",
            "nbf": self.get_current_timestamp(),
            "sub": self.client_id
        }
        token = jwt.JWT(header=header, claims=payload)
        key = self.generate_key()
        token.make_signed_token(key)
        return token

    def get_access_token(self):
        url = "https://login.microsoftonline.com/{}/oauth2/v2.0/token".format(self.tenant_id)

        header = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "Scope": "{}/.default".format(self.client_id),
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": self.get_client_assertion()
        }

        response = requests.post(url, headers=header, data=data)
        return response.json()

    @staticmethod
    def data_source_extractor(url):
        parsed_url = urlparse(url)
        domain_name = parsed_url.netloc
        if domain_name.startswith("www."):
            domain_name = domain_name[4:]
        return domain_name

    # Create token End



