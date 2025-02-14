import azure.functions as func
import logging
import pandas as pd
from src.funcmain import *
import json
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="ping", methods=['GET'])
async def ping(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Ping request received.')
    return func.HttpResponse("Service is up", status_code=200)

@app.route(route="vehicle/add", methods=["POST"])
async def vehicle_add(req: func.HttpRequest) -> func.HttpResponse:
    logging.info(f"Request received from {req.url}")
    body = req.form
    try:
        response = await add_vehicle(
            body=body
        )

        return func.HttpResponse(json.dumps(response), status_code=200)

    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return func.HttpResponse("Internal server error", status_code=500)


@app.route(route="vehicle/update", methods=["POST"])
async def vehicle_update(req: func.HttpRequest) -> func.HttpResponse:
    logging.info(f"Request received from {req.url}")

    body = req.get_json()
    try:
        response = await update_vehicle(body)

        return func.HttpResponse(json.dumps(response.json()), status_code=response.status_code)

    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")

        return func.HttpResponse(json.dumps({"status": "error","code": 500,"message": str(e)}), status_code=500)

