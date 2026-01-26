using './main.bicep'

param environmentName = readEnvironmentVariable('AZURE_ENV_NAME', 'default-env')

param location = readEnvironmentVariable('AZURE_LOCATION', 'westus')

param appSettings = {
  ENVIRONMENT: readEnvironmentVariable('ENVIRONMENT', 'development')
  DB_USER: readEnvironmentVariable('DB_USER', 'postgres')
  DB_PASSWORD: readEnvironmentVariable('DB_PASSWORD', 'postgres')
  DB_HOST: readEnvironmentVariable('DB_HOST', 'localhost')
  DB_PORT: readEnvironmentVariable('DB_PORT', '5432')
  DB_NAME: readEnvironmentVariable('DB_NAME', 'investlogix')
  JWT_SECRET_KEY: readEnvironmentVariable('JWT_SECRET_KEY', 'your-secret-key')
  JQUANTS_API_KEY: readEnvironmentVariable('JQUANTS_API_KEY', 'your-jquants-api-key')
  ALPHAVANTAGE_API_KEY: readEnvironmentVariable('ALPHAVANTAGE_API_KEY', 'your-alphavantage-api-key')
  LINE_CHANNEL_ACCESS_TOKEN: readEnvironmentVariable('LINE_CHANNEL_ACCESS_TOKEN', 'your-line-channel-access-token')
  CORS_ORIGINS: readEnvironmentVariable('CORS_ORIGINS', '["http://localhost:3000"]')
}

param appServicePlanName = readEnvironmentVariable('AZURE_APPSERVICEPLAN_NAME', '')
param appServicePlanResourceGroupName  = readEnvironmentVariable('AZURE_APPSERVICEPLAN_RG', '')
