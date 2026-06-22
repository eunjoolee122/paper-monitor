function Show($scope) {
    if ($scope -eq 'Process') {
        $v = $env:KAGGLE_API_TOKEN
    } else {
        $v = [Environment]::GetEnvironmentVariable('KAGGLE_API_TOKEN', $scope)
    }
    if ($v) {
        $prefix = $v.Substring(0, [Math]::Min(5, $v.Length))
        Write-Host ("{0,-10} : set    len={1,3}  prefix='{2}...'" -f $scope, $v.Length, $prefix)
    } else {
        Write-Host ("{0,-10} : NOT set" -f $scope)
    }
}
Show 'User'
Show 'Machine'
Show 'Process'
