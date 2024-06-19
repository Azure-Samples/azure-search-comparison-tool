import json

class Approaches:
    def __init__(self, json_file_path):
        self.json_file_path = json_file_path
        self.approaches = []
        self.__load_json()

    def __load_json(self):
        with open(self.json_file_path, 'r') as file:
            self.approaches = json.load(file)

    def get_approaches(self):
        return self.approaches
    
    def get(self, approach: str):

        for a in self.approaches:
            if a["key"].lower() == approach.lower():
                return a
        
        raise Exception(f"Approach {approach} is not supported")
