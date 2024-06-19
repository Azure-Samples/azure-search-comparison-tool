import json
import os, glob
from postgres import Postgres
from urllib.parse import quote_plus
import pandas as pd

POSTGRES_SERVER_NAME = os.environ.get("POSTGRES_SERVER")
POSTGRES_SERVER_ADMIN_NAME = os.environ.get("POSTGRES_SERVER_ADMIN_LOGIN")
POSTGRES_SERVER_ADMIN_PASSWORD = os.environ.get("POSTGRES_SERVER_ADMIN_PASSWORD")

POSTGRES_CMS_SERVER_NAME = os.environ.get("POSTGRES_CMS_SERVER")
POSTGRES_CMS_ADMIN_NAME = os.environ.get("POSTGRES_CMS_ADMIN_LOGIN")
POSTGRES_CMS_ADMIN_PASSWORD = os.environ.get("POSTGRES_CMS_ADMIN_PASSWORD")

results_db_connection = Postgres(f"postgresql://{POSTGRES_SERVER_ADMIN_NAME}:{quote_plus(POSTGRES_SERVER_ADMIN_PASSWORD)}@{POSTGRES_SERVER_NAME}.postgres.database.azure.com:5432/postgres?sslmode=require")
wagtail_db_connection = Postgres(f"postgresql://{quote_plus(POSTGRES_CMS_ADMIN_NAME)}:{quote_plus(POSTGRES_CMS_ADMIN_PASSWORD)}@{POSTGRES_CMS_SERVER_NAME}.postgres.database.azure.com:5432/nhsuk-cms-review-comcomsearchpoc?sslmode=require")

path = './app/backend/data/search_queries'
for filename in glob.glob(os.path.join(path, '*.json')):
   
    print(f"Exporting results from {filename}")

    with open(os.path.join(os.getcwd(), filename), 'r') as f: # open in readonly mode

        for search_query in json.load(f):
          
            query = search_query["query"]

            list = []
            output = []
            rank = 1
            csvFileName = f"./results/search_results_{query}.csv"
            jsonFileName = f"./results/search_results_{query}.json"

            for j in results_db_connection.all(f"select * from public.poc_combined_rrf('{query}')"):
                url = "/" + j[0].replace("_", "/") + "/"
                list.append(url)
                output.append({"url": url, "score": str(j[1]), "rank": rank})
                rank += 1

                sql = f"""
                    SELECT
                    slug,
                    title,
                    url_path
                    FROM public.wagtailcore_page
                    WHERE url_path IN ('{"','".join(list)}')
                """

                for page in wagtail_db_connection.all(sql):
                    # print(page)
                    url = page[2]
                    output_result = next((item for item in output if item.get("url") == url), None)
                    output_result["title"] = page[1]
                    output_result["slug"] = page[0]

            # Save the JSON data to a file
            with open(jsonFileName, 'w') as file:
                json.dump(output, file)

            # Convert the output to a DataFrame
            df = pd.DataFrame(output)

            # Write the DataFrame to a CSV file
            df.to_csv(csvFileName, index=False)

            print(f"Exported '{query}' results to {jsonFileName} and {csvFileName}")

