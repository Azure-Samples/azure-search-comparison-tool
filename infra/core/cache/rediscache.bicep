param name string
param location string = resourceGroup().location
param tags object = {}
param sku object = {
  capacity: 0
  family: 'C'
  name: 'Basic'
}

resource redis 'Microsoft.Cache/redis@2023-08-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    redisVersion: '6.0'
    sku: sku
    updateChannel: 'Stable'
  }
}

output name string = redis.name
output port int = redis.properties.sslPort
output host string = redis.properties.hostName
output primaryKey string = redis.listKeys().primaryKey
