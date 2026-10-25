$portFile = Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\Power BI Desktop\AnalysisServicesWorkspaces" -Filter "msmdsrv.port.txt" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $portFile) {
    Write-Output "Power BI Analysis Services port file not found."
    exit 0
}

$portRaw = Get-Content $portFile.FullName
$port = ($portRaw -replace '[^0-9]','').Trim()
Write-Output "Power BI Engine Port: $port"

$xml = '<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><Discover xmlns="urn:schemas-microsoft-com:xml-analysis"><RequestType>DBSCHEMA_CATALOGS</RequestType><Restrictions><RestrictionList/></Restrictions><Properties><PropertyList><Content>SchemaData</Content></PropertyList></Properties></Discover></soap:Body></soap:Envelope>'
$headers = @{
    'SOAPAction' = '"urn:schemas-microsoft-com:xml-analysis:Discover"'
    'Content-Type' = 'text/xml; charset=utf-8'
}

try {
    $response = Invoke-RestMethod -Uri "http://localhost:$port/xmla" -Method Post -Body $xml -Headers $headers
    $rows = $response.DiscoverResponse.return.root.row
    Write-Output "Catalogs in Power BI Desktop:"
    $rows | Select-Object CATALOG_NAME, DATE_MODIFIED | Format-Table -AutoSize
} catch {
    Write-Output "Error querying XMLA: $_"
}
