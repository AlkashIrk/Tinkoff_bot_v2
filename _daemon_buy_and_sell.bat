cd /d %~dp0
cls
Title Buy and Sell
venv\Scripts\python.exe buy_and_candles.py -cfg cfg/alkash.ini -mode buy_and_sell
pause