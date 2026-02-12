FROM python:3.11-slim
WORKDIR /app
COPY digikey_mcp_server.py .
RUN pip install --no-cache-dir fastmcp requests python-dotenv
LABEL io.docker.server.metadata='{"name":"digikey","description":"DigiKey component search, pricing, and datasheets via API","command":["python","digikey_mcp_server.py"],"secrets":[{"name":"digikey.CLIENT_ID","env":"CLIENT_ID"},{"name":"digikey.CLIENT_SECRET","env":"CLIENT_SECRET"}],"env":[{"name":"USE_SANDBOX","value":"false"},{"name":"DIGIKEY_LOCALE_SITE","value":"US"},{"name":"DIGIKEY_LOCALE_LANGUAGE","value":"en"},{"name":"DIGIKEY_LOCALE_CURRENCY","value":"USD"}]}'
CMD ["python", "digikey_mcp_server.py"]
