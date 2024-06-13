targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

param resourceGroupName string = ''

param appServicePlanName string = ''
param backendServiceName string = ''

param searchServiceName string = ''
param searchServiceResourceGroupName string = ''
param searchServiceResourceGroupLocation string = location
param searchServiceSkuName string // Set in main.parameters.json
param searchCombinedIndexName string // Set in main.parameters.json
param searchConditionsIndexName string // Set in main.parameters.json

param openAiServiceName string = ''
param openAiResourceGroupName string = ''
param openAiSkuName string // Set in main.parameters.json

@description('Location for the OpenAI resource group')
@allowed(['canadaeast', 'eastus', 'francecentral', 'uksouth', 'northcentralus', 'southcentralus', 'westeurope'])
@metadata({
  azd: {
    type: 'location'
  }
})
param openAiResourceGroupLocation string

param embeddingDeploymentName string = 'embedding'
param embeddingDeploymentCapacity int = 30
param embeddingModelName string = 'text-embedding-ada-002'

param largeEmbeddingDeploymentName string = 'embedding-large'
param largeEmbeddingDeploymentCapacity int = 30
param largeEmbeddingModelName string = 'text-embedding-3-large'

@description('Id of the user or app to assign application roles')
param principalId string = ''

@description('Flag to decide where to create roles for current user')
param createRoleForUser bool = true

param redisCacheName string = ''
param redisSkuName string = 'Basic'
param redisSkuCapacity int = 1

param resultsDBServerName string = ''
param resultsDBAdminLogin string = ''
@secure()
param resultsDBAdminPassword string

var abbrs = loadJsonContent('./abbreviations.json')

param utcShort string = utcNow('d')

// tags that should be applied to all resources.
var tags = { 
  'azd-env-name': environmentName
  owner: 'martin.smyllie@nhschoices.net'
  'cost code': 'P0840/01'
  'created date': utcShort
  'product owner': 'Martin Smyllie'
  'requested by': 'Martin Smyllie'
  'service-product': 'nhsuk site search poc'
  team: 'PH-CC'
  'created by': 'Martin Smyllie'
  environment: 'Architecture'
}

// Generate a unique token to be used in naming resources.
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

// Organize resources in a resource group
resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

resource openAiResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(openAiResourceGroupName)) {
  name: !empty(openAiResourceGroupName) ? openAiResourceGroupName : resourceGroup.name
}

resource searchServiceResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(searchServiceResourceGroupName)) {
  name: !empty(searchServiceResourceGroupName) ? searchServiceResourceGroupName : resourceGroup.name
}

// Create an App Service Plan to group applications under the same payment plan and SKU
module appServicePlan 'core/host/appserviceplan.bicep' = {
  name: 'appserviceplan'
  scope: resourceGroup
  params: {
    name: !empty(appServicePlanName) ? appServicePlanName : '${abbrs.webServerFarms}${resourceToken}'
    location: location
    tags: tags
    sku: {
      name: 'B1'
      capacity: 1
    }
    kind: 'linux'
  }
}

module openAi 'core/ai/aiservices.bicep' = {
  name: 'openai'
  scope: openAiResourceGroup
  params: {
    name: !empty(openAiServiceName) ? openAiServiceName : 'ai-${resourceToken}'
    location: openAiResourceGroupLocation
    tags: tags
    sku: {
      name: openAiSkuName
    }
    deployments: [
      {
        name: embeddingDeploymentName
        model: {
          format: 'OpenAI'
          name: embeddingModelName
          version: '2'
        }
        capacity: embeddingDeploymentCapacity
      },{
        name: largeEmbeddingDeploymentName
        model: {
          format: 'OpenAI'
          name: largeEmbeddingModelName
          version: '1'
        }
        capacity: largeEmbeddingDeploymentCapacity
      }
    ]
  }
}

// The application frontend
module backend 'core/host/appservice.bicep' = {
  name: 'web'
  scope: resourceGroup
  params: {
    name: !empty(backendServiceName) ? backendServiceName : '${abbrs.webSitesAppService}backend-${resourceToken}'
    location: location
    tags: union(tags, { 'azd-service-name': 'backend' })
    appServicePlanId: appServicePlan.outputs.id
    runtimeName: 'PYTHON'
    runtimeVersion: '3.12'
    appCommandLine: 'python3 -m gunicorn main:app'
    scmDoBuildDuringDeployment: true
    managedIdentity: true
    appSettings: {
      AZURE_OPENAI_SERVICE: openAi.outputs.name
      AZURE_OPENAI_DEPLOYMENT_NAME: embeddingDeploymentName
      AZURE_SEARCH_SERVICE_ENDPOINT: searchService.outputs.endpoint
      AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME: searchConditionsIndexName
      AZURE_SEARCH_NHS_COMBINED_INDEX_NAME: searchCombinedIndexName
    }
  }
}

module searchService 'core/search/search-services.bicep' = {
  name: 'search-service'
  scope: searchServiceResourceGroup
  params: {
    name: !empty(searchServiceName) ? searchServiceName : 'acsvector-${resourceToken}'
    location: searchServiceResourceGroupLocation
    tags: tags
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    sku: {
      name: searchServiceSkuName
    }
    semanticSearch: 'free'
  }
}

// Add Azure Redis Cache
module redisCache 'core/cache/rediscache.bicep' = {
  name: 'redis-cache'
  scope: resourceGroup
  params: {
    name: !empty(redisCacheName) ? redisCacheName : 'redis-${resourceToken}'
    location: location
    tags: tags
    sku: {
      name: redisSkuName
      family: 'C'
      capacity: redisSkuCapacity
    }
  }
}

// Add Azure Postgres DB
module postgres 'core/db/flexible_postgres.bicep' = {
  name: 'results-db'
  scope: resourceGroup
  params: {
    administratorLogin: !empty(resultsDBAdminLogin) ? resultsDBAdminLogin : 'resultsadmin'
    administratorLoginPassword: resultsDBAdminPassword
    serverName: !empty(resultsDBServerName) ? resultsDBServerName : 'postgres-${resourceToken}'
    haMode: 'Disabled'
    serverEdition: 'Burstable'
    dbInstanceType: 'Standard_B1ms'
  }
}

// USER ROLES
module openAiRoleUser 'core/security/role.bicep' = if (createRoleForUser) {
  scope: openAiResourceGroup
  name: 'openai-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
    principalType: 'User'
  }
}

module searchRoleUser 'core/security/role.bicep' = if (createRoleForUser) {
  scope: searchServiceResourceGroup
  name: 'search-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
    principalType: 'User'
  }
}

module searchContribRoleUser 'core/security/role.bicep' = if (createRoleForUser) {
  scope: searchServiceResourceGroup
  name: 'search-contrib-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
    principalType: 'User'
  }
}

module searchSvcContribRoleUser 'core/security/role.bicep' = if (createRoleForUser) {
  scope: searchServiceResourceGroup
  name: 'search-svccontrib-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
    principalType: 'User'
  }
}

// SYSTEM IDENTITIES
module openAiRoleBackend 'core/security/role.bicep' = {
  scope: openAiResourceGroup
  name: 'openai-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
    principalType: 'ServicePrincipal'
  }
}


module searchRoleBackend 'core/security/role.bicep' = {
  scope: searchServiceResourceGroup
  name: 'search-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
    principalType: 'ServicePrincipal'
  }
}

module searchSvcContribRoleBackend 'core/security/role.bicep' = {
  scope: searchServiceResourceGroup
  name: 'search-svccontrib-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
    principalType: 'ServicePrincipal'
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = resourceGroup.name

output AZURE_OPENAI_SERVICE string = openAi.outputs.name
output AZURE_OPENAI_DEPLOYMENT_NAME string = embeddingDeploymentName
output AZURE_OPENAI_DEPLOYMENT_LARGE_NAME string = largeEmbeddingDeploymentName

output AZURE_SEARCH_SERVICE_ENDPOINT string = searchService.outputs.endpoint
output AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME string = searchConditionsIndexName
output AZURE_SEARCH_NHS_COMBINED_INDEX_NAME string = searchCombinedIndexName 

output REDIS_HOST string = redisCache.outputs.host
output REDIS_PORT int = redisCache.outputs.port
output REDIS_PRIMARYKEY string = redisCache.outputs.primaryKey

output POSTGRES_SERVER string = postgres.outputs.name
output POSTGRES_SERVER_ADMIN_LOGIN string = resultsDBAdminLogin
output POSTGRES_SERVER_ADMIN_PASSWORD string = resultsDBAdminPassword
