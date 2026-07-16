@echo off
rem ===========================================================================
rem  Iniciar Saude MEI - basta dar DUPLO CLIQUE neste arquivo.
rem  Ele faz sozinho: instala as dependencias (se faltarem), treina o modelo
rem  de IA (se ainda nao existir) e abre o site no navegador.
rem  Para DESLIGAR o servidor: volte nesta janela preta e aperte Ctrl+C.
rem ===========================================================================
title Saude MEI
cd /d "%~dp0"

rem --- 1) Confere se o Python esta instalado -------------------------------
where py >nul 2>nul
if errorlevel 1 (
    echo.
    echo  ERRO: Python nao encontrado neste computador.
    echo  Instale em https://www.python.org/downloads/
    echo  ^(marque a opcao "Add python.exe to PATH" na instalacao^)
    echo.
    pause
    exit /b 1
)

echo.
echo  [1/3] Conferindo dependencias (rapido se ja estiverem instaladas)...
py -m pip install -r requirements.txt --quiet --disable-pip-version-check

rem --- 2) Treina o modelo de IA apenas na primeira vez ----------------------
if exist "modelos\classificador.joblib" (
    echo  [2/3] Modelo de IA ja treinado - ok.
) else (
    echo  [2/3] Treinando o modelo de IA pela primeira vez, aguarde ~1 min...
    py treinar.py
)

rem --- 3) Abre o navegador (com 3s de espera para o servidor subir) e roda --
echo  [3/3] Iniciando o servidor... O site vai abrir sozinho no navegador.
echo.
echo  No SEU computador:            http://127.0.0.1:5000
echo  Outras pessoas na MESMA rede: http://SEU-IP:5000 (IP aparece abaixo)
echo.
rem (o ping serve so como "espera de 3 segundos" antes de abrir o navegador)
start "" /b cmd /c "ping -n 4 127.0.0.1 >nul & start http://127.0.0.1:5000"
py app.py

pause
