@echo off
title Launch Smart Supply Chain Power BI Dashboard
echo ======================================================================
echo Launching Smart Supply Chain Power BI Project (.pbip)
echo ======================================================================
echo.
echo Opening SmartSupplyChain.pbip in Microsoft Power BI Desktop...

start "" "C:\Program Files\Microsoft Power BI Desktop\bin\PBIDesktop.exe" "%~dp0SmartSupplyChain.pbip"

echo.
echo Power BI Desktop launched successfully!
echo If prompted with "Apply Changes", click "Apply changes" to refresh data.
timeout /t 5
