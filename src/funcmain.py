import logging
from recommendation import BuyerRecommendation
from models import *
from utils import *
from pyzohocrm import TokenManager, ZohoApi
import os
from dotenv import load_dotenv
load_dotenv()
import requests
from PIL import Image
import io
import asyncio
TEMP_DIR = "/tmp/"

TOKEN_INSTANCE =  TokenManager(
                                domain_name="Canada",
                                refresh_token=os.getenv("REFRESH_TOKEN"),
                                client_id=os.getenv("CLIENT_ZOHO_ID"),
                                client_secret=os.getenv("CLIENT_ZOHO_SECRET"),
                                grant_type="refresh_token",
                                token_dir=TEMP_DIR
                                )

buyer_instance = BuyerRecommendation()  

ZOHO_API = ZohoApi(base_url="https://www.zohoapis.ca/crm/v2")



## temp fix
async def send_vehicle_to_leads(vehicle_row):
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, requests.post, 
                         "https://tradegeek-leads.azurewebsites.net/api/leads/add?code=3BA6F_8jxMl5cC7cEP8vhbBxIUPFIXoWaS0239o3u2QRAzFuPa52fQ%3D%3D", 
                         vehicle_row)


async def add_vehicle(body):
        """ Processes vehicle and lead request"""
        try:
            # Get the access token
            access_token=TOKEN_INSTANCE.get_access_token()

            logging.info(f"received form data: {body}")
            logging.info(f"Buyer fee {type(body.get('Buyer_Fee',''))}")
            # Create Vehicle instance from form data
            vehicle = Vehicle(
                Vehicle_Image_Url=body.get('Vehicle_Image_Url', ''),
                Mileage=body.get('Mileage',''),
                Purchase_Price_f=body.get('purchase_price',''),
                Name=body.get('Name',''),
                Make=body.get('Make',''),
                Model=body.get('Model',''),
                Year=body.get('Year',''),
                VIN=body.get('VIN',''),
                Notes=body.get('Notes',''),
                Body_Type=body.get('Body_Type',''),
                Pickup_Location=body.get('Pickup_Location',''),
                DisplacementL=body.get('DisplacementL',''),
                Drivetrain=body.get('Drivetrain',''),
                Transmission=body.get('Transmission',''),
                Tires=body.get('Tires',''),
                Tire_Condition=body.get('Tire_Condition',''),
                Trim=body.get('Trim',''),
                Options=body.get('Options',''),  # If Options is a list
                Declarations=body.get('Declarations',''),
                # Source=body.get('Source',''),
                Source="Website Input",
                Seller_ID=body.get('Seller_ID',''),
                Seller_Name=body.get('SellerName',''),
                VehicleDescription=body.get('VehicleDescription',''),
                VehicleCaptureType=body.get('VehicleCaptureType',''),
                ConditionScore=body.get('VehicleConditionScore',''),
                Auction_URL=body.get('Auction_URL',''),
                Auction_Date=format_datetime(body.get('Auction_Date','')),
                Status="Pending Review",
                Where_is_the_Vehicle_Now =body.get('Where_is_the_Vehicle_Now',''),
                Does_this_Vehicle_Require_Transport = body.get('Does_this_Vehicle_Require_Transport',''),
                Buyer_Fee_f = float(body.get('Buyer_Fee',0.0)),
                Misc_Fee_f = float(body.get('Misc_Fees',0.0)),
                Transport_Cost_F = float(body.get('Transport_Cost',0.0)),
                Taxes_F = float(body.get('Taxes',0.0)),
                Image_Link= process_main_img(body.get('Vehicle_Image_Url','')),
                Exterior_colour=body.get('Exterior_Color', ''),
                Number_of_Cylinders=body.get('Number_of_Cylinders', ''),
                Number_of_Doors=body.get('Number_of_Doors', ''),
                Number_of_Passengers=body.get('Number_of_Passengers', '')

            )
            # Convert Vehicle instance to a dictionary
            bubble_vehicle = dict(vehicle)
       
            main_image_url = process_main_img(vehicle.Vehicle_Image_Url)
            vehicle_response = ZOHO_API.create_record(moduleName="Vehicles", data={"data": [bubble_vehicle]}, token=access_token)
            logging.info(f"Vehicle Response : {vehicle_response.json()}")
            vehicle_id = vehicle_response.json()['data'][0]['details']['id']
            def attach_main_image_to_vehicle(access_token, vehicle_id, image_url):
                temp_image_path = os.path.join(TEMP_DIR, f"{vehicle_id}.jpg")
                logging.info(f"Temp Image Path : {temp_image_path}")
                def resize_and_save_image(image_url, vehicle_id, max_width=1024, max_height=1024):
                    response = requests.get(image_url)
                    img = Image.open(io.BytesIO(response.content))

                    # Resize while maintaining aspect ratio
                    img.thumbnail((max_width, max_height))

                    # Save as JPEG
                    img = img.convert("RGB")
                    
                    img.save(temp_image_path, "JPEG", quality=85)

                resize_and_save_image(image_url, vehicle_id)  # Resize before uploading

                url = f"https://www.zohoapis.ca/crm/v2/Vehicles/{vehicle_id}/photo"
                headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
                files = {"file": (f"{vehicle_id}.jpg", open(temp_image_path, "rb"), "image/jpeg")}

                attach_response = requests.post(url, headers=headers, files=files)
                os.remove(temp_image_path)  # Clean up local file

                logging.info(f"Attach Main Image Response : {attach_response.json()}")
                return attach_response.json()
            
            try:
                vehicle_image_response = attach_main_image_to_vehicle(access_token, vehicle_id, main_image_url)
                logging.info(f"Vehicle Image Response : {vehicle_image_response}")
            except Exception as e:
                logging.error(f"Error Occured While Adding Vehicle Image {e}")
    
            vehicle_row = {
                "id":vehicle_id,
                "Make": vehicle.Make,
                "Model": vehicle.Model,
                "Year": vehicle.Year,
                "Trim": vehicle.Trim.replace('"', '\\"').replace("'", "\\'") , ## resolve parsing errors due
                "Mileage": vehicle.Mileage,
                "Vin":vehicle.VIN,
                "source":vehicle.Source
            }
            asyncio.create_task(send_vehicle_to_leads(vehicle_row))  # Run in background
            return {"details":vehicle_row,"Vehicle ID":vehicle_id,"code":"SUCCESS"}
          
        except Exception as e:
            logging.error(f"Error Occured While Adding Vehicle {e}")
            return {"status": "error","code": 500,"message": str(e)}
  

async def update_vehicle(data):
    vehicle_id = data.get("Vehicle_ID")
    del data["Vehicle_ID"]
    update_response = ZOHO_API.update_record(moduleName="Vehicles", id=vehicle_id, data={"data": [data]}, token=TOKEN_INSTANCE.get_access_token())

    logging.info(f"Update Vehicle Response : {update_response.json()}")

    return update_response



