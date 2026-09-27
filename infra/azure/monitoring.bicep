// -----------------------------------------------------------------------------
// Monitoring for the APIM gateway (Sprint B4).
// Adds a Log Analytics workspace, APIM gateway diagnostic logs, and a metric
// alert on failed (4xx) requests. Deploy into the same resource group as APIM.
// -----------------------------------------------------------------------------

@description('Azure region.')
param location string = resourceGroup().location

@description('Existing APIM service name to monitor.')
param apimName string

@description('Optional Action Group resource id to notify on alerts. Leave empty to create the alert without notifications.')
param actionGroupId string = ''

resource apim 'Microsoft.ApiManagement/service@2023-05-01-preview' existing = {
  name: apimName
}

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${apimName}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource apimDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'apim-gateway-logs'
  scope: apim
  properties: {
    workspaceId: workspace.id
    logs: [
      {
        categoryGroup: 'allLogs'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

resource failedRequestsAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${apimName}-failed-requests'
  location: 'global'
  properties: {
    description: 'Elevated 4xx responses at the APIM gateway (possible auth failures / abuse).'
    severity: 3
    enabled: true
    scopes: [
      apim.id
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'FailedRequests'
          metricName: 'Requests'
          dimensions: [
            {
              name: 'GatewayResponseCodeCategory'
              operator: 'Include'
              values: [
                '4xx'
              ]
            }
          ]
          operator: 'GreaterThan'
          threshold: 50
          timeAggregation: 'Total'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: empty(actionGroupId) ? [] : [
      {
        actionGroupId: actionGroupId
      }
    ]
  }
}

output workspaceId string = workspace.id
