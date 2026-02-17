FROM python:3.11-slim
WORKDIR /app
COPY *.py .
RUN pip install --no-cache-dir fastmcp requests python-dotenv
LABEL io.docker.server.metadata='{"name":"digikey","description":"DigiKey component search, pricing, ordering, and order status","command":["python","digikey_mcp_server.py"],"secrets":[{"name":"digikey.CLIENT_ID","env":"CLIENT_ID"},{"name":"digikey.CLIENT_SECRET","env":"CLIENT_SECRET"},{"name":"digikey.DIGIKEY_ACCOUNT_ID","env":"DIGIKEY_ACCOUNT_ID"}],"env":[{"name":"USE_SANDBOX","value":"false"},{"name":"DIGIKEY_LOCALE_SITE","value":"US"},{"name":"DIGIKEY_LOCALE_LANGUAGE","value":"en"},{"name":"DIGIKEY_LOCALE_CURRENCY","value":"USD"}]}'
CMD ["python", "digikey_mcp_server.py"]
