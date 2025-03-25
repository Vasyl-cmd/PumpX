# Функция для проверки подключения к интернету
function Test-InternetConnection {
    try {
        $ping = Test-Connection -ComputerName google.com -Count 1 -Quiet
        return $ping
    } catch {
        return $false
    }
}

# Проверка подключения каждую секунду до тех пор, пока интернет не станет доступен
while (-not (Test-InternetConnection)) {
    Write-Host "Нет интернета. Пытаемся снова..."
    Start-Sleep -Seconds 1
}

# Запуск бота, когда интернет подключен
Start-Process "C:\Users\vasil\CryptoBot\start_bot.bat"