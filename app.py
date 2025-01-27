from flask import Flask, render_template, request, redirect, url_for, session
import requests

app = Flask(__name__)
app.secret_key = "5zli3ji59h320xyeu6bss5s9uobd2l5pio03fdbc7cb4jyy9ws"

# RDW API URL
RDW_API_URL = "https://opendata.rdw.nl/resource/m9d7-ebf2.json"

# Onderhoudswerkzaamheden en hun kosten
TASKS = {
    "oil_change": {"label": "Olie verversen + Oliefilter", "cost": 0},
    "microfilter_replacement": {"label": "Microfilter vervangen", "cost": 50},
    "air_filter_replacement": {"label": "Luchtfilter vervangen", "cost": 30},
    "read_error_codes": {"label": "Voertuig storingscodes uitlezen", "cost": 50},
    "tire_inspection": {"label": "Auto inspectie", "cost": 25},
    "apk": {"label": "APK-keuring", "cost": 60},
    "spark_plug_replacement": {"label": "Bougies vervangen", "cost": 0},
    "fuel_filter_replacement": {"label": "Brandstoffilter vervangen", "cost": 75},
    "brake_fluid_replacement": {"label": "Remvloeistof vervangen", "cost": 90},
    "battery_remote_replacement": {"label": "Batterij afstandsbediening vervangen", "cost": 15},
    "brake_inspection": {"label": "Remmeninspectie en -reiniging", "cost": 25},
    "ac_system_check": {"label": "Controle werking aircosysteem", "cost": 15},
}

# Vast uurtarief (kan worden aangepast)
HOURLY_RATE = 85  # Standaard uurtarief in euro's

# VAT percentage
VAT_RATE = 0.21  # 21%

# Helperfunctie: voertuiggegevens ophalen
def fetch_vehicle_data(license_plate):
    try:
        license_plate = license_plate.replace(" ", "").upper()
        response = requests.get(RDW_API_URL, params={"kenteken": license_plate})
        response.raise_for_status()
        data = response.json()
        if data:
            vehicle = data[0]
            brand = vehicle.get("merk", "").lower()
            allowed_brands = ["mini", "bmw", "rolls-royce"]

            if brand not in allowed_brands:
                return {"error": "Bavarian Motors accepteert alleen voertuigen van de merken BMW, MINI en Rolls-Royce. Onze excuses voor het ongemak."}

            return {
                "license_plate": license_plate,
                "model": vehicle.get("handelsbenaming", "Onbekend model"),
                "year": vehicle.get("datum_eerste_toelating", "Onbekend")[:4],
                "cylinders": int(vehicle.get("aantal_cilinders", 0)),
                "oil_capacity": int(vehicle.get("aantal_cilinders", 0)) * 1.5,
            }
    except Exception as e:
        print(f"Fout bij ophalen voertuiggegevens: {e}")
        return None

# Helperfunctie: kosten berekenen
def calculate_cost(work_selections, vehicle_data):
    base_cost = HOURLY_RATE
    oil_cost_per_liter = 20
    spark_plug_cost = 29
    total_cost_excl_vat = base_cost

    if work_selections.get("oil_change"):
        total_cost_excl_vat += vehicle_data["oil_capacity"] * oil_cost_per_liter
    if work_selections.get("spark_plug_replacement"):
        total_cost_excl_vat += vehicle_data["cylinders"] * spark_plug_cost

    for task, data in TASKS.items():
        if work_selections.get(task) and task not in ["oil_change", "spark_plug_replacement"]:
            total_cost_excl_vat += data["cost"]

    total_cost_incl_vat = total_cost_excl_vat * (1 + VAT_RATE)
    return round(total_cost_excl_vat, 2), round(total_cost_incl_vat, 2)

# Route: Onderhoudskosten calculator
@app.route("/", methods=["GET", "POST"])
def calculator():
    if request.method == "POST":
        license_plate = request.form.get("license_plate")
        vehicle_data = fetch_vehicle_data(license_plate)

        # Handle cases where vehicle_data is None
        if vehicle_data is None:
            return render_template(
                "calculator.html",
                tasks=TASKS,
                error="Voertuiggegevens konden niet worden opgehaald. Controleer het kenteken.",
                work_selections={}
            )

        # Handle cases where an error exists in vehicle_data
        if "error" in vehicle_data:
            return render_template(
                "calculator.html",
                tasks=TASKS,
                error=vehicle_data["error"],  # Display specific error
                work_selections={}
            )

        # Save vehicle data and selections in session
        session["vehicle_data"] = vehicle_data
        session["work_selections"] = {
            task: request.form.get(task) == "on" for task in TASKS
        }
        total_cost_excl_vat, total_cost_incl_vat = calculate_cost(session["work_selections"], vehicle_data)
        session["annual_cost_excl_vat"] = total_cost_excl_vat
        session["annual_cost_incl_vat"] = total_cost_incl_vat
        session["monthly_cost_excl_vat"] = round(total_cost_excl_vat / 12, 2)
        session["monthly_cost_incl_vat"] = round(total_cost_incl_vat / 12, 2)

        return redirect(url_for("summary"))

    return render_template("calculator.html", tasks=TASKS, work_selections={})

# Other routes remain unchanged
# ...

# Route: Overzicht
@app.route("/summary", methods=["GET", "POST"])
def summary():
    if request.method == "POST":
        session["payment_option"] = request.form.get("payment_option")
        return redirect(url_for("customer_info"))

    vehicle_data = session.get("vehicle_data")
    if not vehicle_data:
        return redirect(url_for("calculator"))

    return render_template(
        "summary.html",
        vehicle_data=vehicle_data,
        annual_cost_excl_vat=session.get("annual_cost_excl_vat"),
        annual_cost_incl_vat=session.get("annual_cost_incl_vat"),
        monthly_cost_excl_vat=session.get("monthly_cost_excl_vat"),
        monthly_cost_incl_vat=session.get("monthly_cost_incl_vat"),
    )

# Route: Klantgegevens
@app.route("/customer-info", methods=["GET", "POST"])
def customer_info():
    vehicle_data = session.get("vehicle_data")
    if not vehicle_data:
        return redirect(url_for("calculator"))

    if request.method == "POST":
        session["customer_data"] = {
            "name": request.form.get("name"),
            "address": request.form.get("address"),
            "email": request.form.get("email"),
            "iban": request.form.get("iban"),
            "signature": request.form.get("signature"),
        }
        return redirect(url_for("confirmation"))

    return render_template(
        "customer_info.html",
        vehicle_data=vehicle_data,
        payment_option=session.get("payment_option"),
        annual_cost_excl_vat=session.get("annual_cost_excl_vat"),
        annual_cost_incl_vat=session.get("annual_cost_incl_vat"),
        monthly_cost_excl_vat=session.get("monthly_cost_excl_vat"),
        monthly_cost_incl_vat=session.get("monthly_cost_incl_vat"),
    )

# Route: Bevestiging
@app.route("/confirmation", methods=["GET"])
def confirmation():
    customer_data = session.get("customer_data")
    if not customer_data:
        return redirect(url_for("customer_info"))

    vehicle_data = session.get("vehicle_data")
    return render_template(
        "confirmation.html",
        customer_data=customer_data,
        vehicle_data=vehicle_data,
        payment_option=session.get("payment_option"),
        annual_cost_excl_vat=session.get("annual_cost_excl_vat"),
        annual_cost_incl_vat=session.get("annual_cost_incl_vat"),
        monthly_cost_excl_vat=session.get("monthly_cost_excl_vat"),
        monthly_cost_incl_vat=session.get("monthly_cost_incl_vat"),
    )

# Start de Flask-app
if __name__ == "__main__":
    app.run(debug=True)
