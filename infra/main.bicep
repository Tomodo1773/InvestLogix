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
param appServicePlanResourceGroupName string = ''

param appSettings object

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }

// Organize resources in a resource group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}


// ****************************************************************
// AppServicePlan
// ****************************************************************

resource existingAppServicePlan 'Microsoft.Web/serverfarms@2021-02-01' existing = {
  name: appServicePlanName
  scope: resourceGroup(appServicePlanResourceGroupName)
}

module AppServicePlan 'core/appserviceplan.bicep' = if (empty(appServicePlanName)) {
  name: 'AppServicePlan'
  scope: rg
  params: {
    name: '${abbrs.webServerFarms}${resourceToken}'
    location: location
    tags: tags
    skuName: 'F1'
    skuTier: 'Free'
    skuSize: 'F1'
    skuFamily: 'F'
    skuCapacity: 1
    kind: 'linux'
  }
}

// ****************************************************************
// AppService
// ****************************************************************

// The application backend
module AppService './app/api.bicep' = {
  name: 'AppService'
  scope: rg
  params: {
    name: '${abbrs.webSitesAppService}${resourceToken}'
    location: location
    tags: tags
    appServicePlanId: empty(appServicePlanName) ? AppServicePlan.outputs.id : existingAppServicePlan.id
    alwaysOn: true
    appSettings: {
      ENVIRONMENT: appSettings.ENVIRONMENT
      DB_USER: appSettings.DB_USER
      DB_PASSWORD: appSettings.DB_PASSWORD
      DB_HOST: appSettings.DB_HOST
      DB_PORT: appSettings.DB_PORT
      DB_NAME: appSettings.DB_NAME
      JWT_SECRET_KEY: appSettings.JWT_SECRET_KEY
      JQUANTS_API_KEY: appSettings.JQUANTS_API_KEY
      ALPHAVANTAGE_API_KEY: appSettings.ALPHAVANTAGE_API_KEY
      LINE_CHANNEL_ACCESS_TOKEN: appSettings.LINE_CHANNEL_ACCESS_TOKEN
      CORS_ORIGINS: appSettings.CORS_ORIGINS
    }
  }
}


// App outputs
