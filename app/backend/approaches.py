import json

class Approaches:
    def __init__(self, json_file_path):
        self.json_file_path = json_file_path
        self.approaches = []
        self.load_json()

    def load_json(self):
        with open(self.json_file_path, 'r') as file:
            self.approaches = json.load(file)

    def get_approaches(self):
        return self.approaches
