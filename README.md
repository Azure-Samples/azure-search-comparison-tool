# Azure AI Search Comparison Tool

This repository contains a React application that demonstrates the Azure AI Search Comparison Tool. This tool provides a web interface for visualizing different retrieval modes available in Azure AI Search. Additionally, the tool supports image search using text-to-image and image-to-image search functionalities. It leverages Azure OpenAI for text embeddings and Azure AI Vision API for image embeddings.

You can find a live demo at [aka.ms/VectorSearchDemo](https://aka.ms/VectorSearchDemo/)

![Vector Search Video](https://github.com/Azure-Samples/azure-search-comparison-tool/blob/main/public/VectorGIF.gif)

## Features

- Generate text embeddings using Azure OpenAI and insert them into a vector store in Azure AI Search.
- Perform vector search queries on text data, including vector searches with metadata filtering and hybrid (text + vectors) search.
- Generate image embeddings using Azure AI Vision API.
- Perform text-to-image and image-to-image vector searches.

## Prerequisites

- An Azure subscription with access to Azure AI Search and Azure AI Services.
- Access to Azure OpenAI for generating text embeddings.
- Access to Azure AI Vision for generating image embeddings.

To run this demo locally, you will need the following:

- [Azure Developer CLI](https://aka.ms/azure-dev/install)
- [Python 3.9+](https://www.python.org/downloads/)
  - **Important**: Python and the pip package manager must be in the path in Windows for the setup scripts to work.
  - **Important**: Ensure you can run `python --version` from console. On Ubuntu, you might need to run `sudo apt install python-is-python3` to link `python` to `python3`.
- [Node.js 14+](https://nodejs.org/en/download/)
- [Git](https://git-scm.com/downloads)
- [Powershell 7+ (pwsh)](https://github.com/powershell/powershell) - For Windows users only.
  - **Important**: Ensure you can run `pwsh.exe` from a PowerShell command. If this fails, you likely need to upgrade PowerShell.

## Setup

### Starting from scratch

Execute the following commands, if you don't have any pre-existing Azure services and want to start from a fresh deployment.

1. Clone this repository to your local machine.
1. Run `azd auth login`
1. Run `azd up` - This will provision Azure resources and deploy this demo to those resources
1. After the application has been successfully deployed you will see a URL printed to the console. Click that URL to interact with the application in your browser.

   > NOTE: It may take a minute for the application to be fully deployed. If you see a "Python Developer" welcome screen, then wait a minute and refresh the page.

### Using existing resources

1. Run `azd env set AZURE_OPENAI_SERVICE {Name of existing Azure OpenAI service}`
1. Run `azd env set AZURE_OPENAI_DEPLOYMENT_NAME {Name of existing embedding model deployment}`. Only needed if your deployment is not the default 'embeddings'. Typically this'll be a text-embedding-ada-002 model.
1. Run `azd env set AZURE_SEARCH_SERVICE_ENDPOINT {Endpoint of existing Azure AI Search service}`
1. Run `azd up`

### Deploying again

If you've only changed the backend/frontend code in the `app` folder, then you don't need to re-provision the Azure resources. You can just run:

`azd deploy`

If you've changed the infrastructure files (`infra` folder or `azure.yaml`), then you'll need to re-provision the Azure resources. You can do that by running:

`azd up`

### Running locally

1. Run `azd auth login`
1. Change dir to `app`
1. Run `./start.ps1` or `./start.sh` or run the "VS Code Task: Start App" to start the project locally.

### Running locally with hot reloading

This is recommended only for development, and provides hot reloading of both backend and frontend:

In one terminal run the backend:

1. Run `azd auth login`
1. Change dir to `app`
1. Run `./start.ps1` or `./start.sh`

In a second terminal run the frontend:

1. Change dir to `app/frontend`
1. Run `npm start`
1. Use website from <https://localhost:5173/>

## Usage

- In Azure: navigate to the Azure WebApp deployed by azd. The URL is printed out when azd completes (as "Endpoint"), or you can find it in the Azure portal.
- Running locally: navigate to 127.0.0.1:50505

1. The Azure Search Comparison Tool allows you to search for text queries by entering them in the search bar and pressing 'Enter'. The application will generate text embeddings using Azure OpenAI and perform vector searches on the data stored in Azure AI Search.

1. The search results will be displayed as cards. Feel free to click on the settings icon to explore the different query approaches such as Hybrid Search and Hybrid Search with Semantic Ranking, Captions, and Highlights powered by Microsoft Bing. Note that you will need to enroll in a Semantic Plan in your Azure AI Search service to use this feature. See [Semantic search](https://learn.microsoft.com/azure/search/semantic-search-overview).

## Conclusion

We hope you find this repository useful for demoing Vector search and exploring the different features Azure AI Search has to offer. Feel free to explore and customize the code to meet your specific requirements.  
If you have any questions or suggestions, please feel free to open an issue and we'll be happy to help.

Happy searching!

## References

- [Azure AI Search Documentation](https://learn.microsoft.com/azure/search/)
- [Azure OpenAI Documentation](https://learn.microsoft.com/azure/ai-services/openai/)
- [Azure AI Vision Documentation](https://learn.microsoft.com/azure/ai-services/computer-vision/)
