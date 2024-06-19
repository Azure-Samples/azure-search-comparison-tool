import json
import os, glob
import requests
import ast

with open("./app/backend/data/approaches.json", 'r') as f:
    approaches = json.load(f)

path = './app/backend/data/search_queries'
for filename in glob.glob(os.path.join(path, '*.json')):
   
   print(filename)

   with open(os.path.join(os.getcwd(), filename), 'r') as f: # open in readonly mode

      for search_query in json.load(f):
         query = search_query["query"]

         for a in approaches:
            # do the search
            print(f"Searching for '{query}' using '{a["title"]}' ({a["key"]})")

            search_request_body = {
                "query": query,
                "approach": a["key"],
                "k": 20
            }

            if "data_set" in a:
               search_request_body["dataSet"] = a["data_set"]

            if "use_vector_search" in a and a["use_vector_search"] == True:

                vector_request_body = { "query": query, "approach": a["key"] }

                print(f"embedding query: {vector_request_body}")

                response = requests.post("http://127.0.0.1:5000/embedQuery", json=vector_request_body)

                if response.status_code == 200:
                    print(f"successful embedding query for: {query}")

                    search_request_body["queryVector"] = list(ast.literal_eval(  response.text))
                else:
                   raise Exception(f"embedding query fail {response.status_code}")
                    

            search_response = requests.post("http://127.0.0.1:5000/searchText", json=search_request_body)

            if search_response.status_code == 200:
               print("success")
            else:
               raise Exception(f"Search failed. status {search_response.status_code} {search_response.text}")
 