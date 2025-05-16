import requests
import json
from airflow.hooks.base import BaseHook
from airflow.exceptions import AirflowException
import logging

# CLASS TO CONNECT TO AMADEUS API AND FETCH FLIGHTS
class AmadeusAPI:
    def __init__(self, conn_id):
        self.conn_id = conn_id
        self.token_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        self.api_url = "https://test.api.amadeus.com/v2/shopping/flight-offers"

    # PREPARE ACCESS TOKEN
    def get_token(self):
        try:
            conn = BaseHook.get_connection(self.conn_id)
            extras = conn.extra_dejson

            payload = f"grant_type=client_credentials&client_id={extras.get('api_key')}&client_secret={extras.get('api_secret')}"
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            response = requests.post(
                self.token_url, headers=headers, data=payload)

            if response.status_code != 200:
                raise AirflowException("Error to get token: Invalid response")

            token = response.json().get('access_token')
            if not token:
                raise AirflowException("Error to get token: No token")

            return token

        except Exception as e:
            print(f"Error to get token: {e}")

    # GET PROMOTIONAL FLIGHTS WITH PERSONAL PARAMETERS
    def get_flights(self, origin, destination, departure_date, adults=1, currency_code="BRL", max=12):
        try:
            token = self.get_token()
            headers = {'Authorization': f'Bearer {token}'}
            params = {
                'originLocationCode': origin,
                'destinationLocationCode': destination,
                'departureDate': departure_date,
                'adults': adults,
                'currencyCode': currency_code,
                "max": max
            }
            response = requests.get(
                self.api_url, headers=headers, params=params)
            if response.status_code != 200:
                raise AirflowException(
                    "Error to get flights: Invalid response")

            return response.json()

        except Exception as e:
            print(f"Error to get flights: {e}")

    # GET THE JSON RETURN AND APPLY PRE PROCESS
    def data_processing(self, origin, destination, departure_date):
        data_json_api = self.get_flights(
            origin=origin, destination=destination, departure_date=departure_date)

        if not data_json_api or "data" not in data_json_api:
            logging.warning("No data returned from API")
            return {}

        for flight in data_json_api.get("data", []):
            for traveler in flight.get("travelerPricings", []):
                traveler.pop("fareDetailsBySegment", None)

        # COLECT IMPORTANT DATA FROM JSON RETURN
        flights = {}
        for flight in data_json_api.get("data", []):
            id_flight = flight.get("id")
            lastTicketingDate = flight.get("lastTicketingDate", None)
            totalPrice = flight.get("price", None).get("total", None)
            basePrice = flight.get("price", None).get("base", None)
            numberOfBookableSeats = flight.get("numberOfBookableSeats", None)
            checkedbags = flight.get("pricingOptions", {}).get(
                "includedCheckedBagsOnly", None)

            segments = []
            for itineraries in flight.get("itineraries", []):
                for segment in itineraries.get("segments", []):
                    segments.append({
                        "departure": segment.get("departure", {}).get("iataCode", None),
                        "arrival": segment.get("arrival", {}).get("iataCode", None),
                    })

            flights[flight.get("id")] = {
                "id": id_flight,
                "lastTicketingDate": lastTicketingDate,
                "totalPrice": totalPrice,
                "basePrice": basePrice,
                "numberOfBookableSeats": numberOfBookableSeats,
                "checkedbags": checkedbags,
                "segments": segments
            }

        return flights
