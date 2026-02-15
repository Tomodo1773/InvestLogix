param name string
param location string = resourceGroup().location
param tags object = {}

param appCommandLine string = 'PYTHONPATH="/home/site/wwwroot/site-packages:$PYTHONPATH" gunicorn --workers 1 --timeout 120 --access-logfile "-" --error-logfile "-" --bind=0.0.0.0:8000 -k uvicorn.workers.UvicornWorker stock.app:app'
param appServicePlanId string
@secure()
param appSettings object = {}
param serviceName string = 'api'

param alwaysOn bool
module api '../core/appservice.bicep' = {
  name: 'api'
  params: {
    name: name
    location: location
    tags: union(tags, { 'azd-service-name': serviceName })
    appCommandLine: appCommandLine
    appServicePlanId: appServicePlanId
    appSettings: appSettings
    runtimeName: 'python'
    runtimeVersion: '3.13'
    scmDoBuildDuringDeployment: false
    enableOryxBuild: false
    alwaysOn: alwaysOn
  }
}
