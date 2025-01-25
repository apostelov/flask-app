from flask import Flask, render_template, request, redirect, url_for, session
import requests

app = Flask(__name__)
app.secret_key = "5zli3ji59h320xyeu6bss5s9uobd2l5pio03fdbc7cb4jyy9ws"

# RDW API URL
RDW_API_URL = "https://opendata.rdw.nl/resource/m9d7-ebf2.json"

# Onderhoudswerkzaamheden en hun kosten
TASKS = {
    "oil_change": {"label": "Olie verversen", "cost": 50},
    "spark_plug_replacement": {"label": "Bougies vervangen", "cost": 75},
    "microfilter_replacement": {"label": "Microfilter vervangen", "cost": 45},
    "air_filter_replacement": {"label": "Luchtfilter vervangen", "cost": 30},
    "apk": {"label": "APK-keuring", "cost": 60},
    "fuel_filter_replacement": {"label": "Brandstoffilter vervangen", "cost": 75},
    "brake_fluid_replacement": {"label": "Remvloeistof vervangen", "cost": 90},
    "battery_remote_replacement": {"label": "Batterij afstandsbediening vervangen", "cost": 15},
    "read_error_codes": {"label": "Voertuig storingscodes uitlezen", "cost": 50},
    "brake_inspection": {"label": "Remmeninspectie en -reiniging", "cost": 25},
    "tire_inspection": {"label": "Banden inspectie", "cost": 25},
    "ac_system_check": {"label": "Controle werking aircosysteem", "cost": 15},
}

# Vast uurtarief (kan worden aangepast)
HOURLY_RATE = 75  # Standaard uurtarief in euro's

# Helperfunctie: voertuiggegevens ophalen
def fetch_vehicle_data(license_plate):
    try:
        license_plate = license_plate.replace(" ", "").upper()
        response = requests.get(RDW_API_URL, params={"kenteken": license_plate})
        response.raise_for_status()
        data = response.json()
        if data:
            vehicle = data[0]
            return {
                "license_plate": license_plate,
                "model": vehicle.get("handelsbenaming", "Onbekend model"),
                "year": vehicle.get("datum_eerste_toelating", "Onbekend")[:4],
                "apk_expiration": vehicle.get("vervaldatum_apk", "Onbekend"),
            }
    except Exception as e:
        print(f"Fout bij ophalen voertuiggegevens: {e}")
        return None

# Helperfunctie: kosten berekenen
def calculate_cost(work_selections):
    hourly_rate = session.get("hourly_rate", HOURLY_RATE)  # Gebruik sessie of standaard
    task_cost = sum(
        TASKS[task]["cost"] for task, selected in work_selections.items() if selected
    )
    total_cost = task_cost + hourly_rate
    return round(total_cost, 2)

# Dynamisch uurtarief instellen
@app.route("/set-hourly-rate", methods=["POST"])
def set_hourly_rate():
    rate = request.form.get("hourly_rate")
    if rate and rate.isdigit():
        session["hourly_rate"] = int(rate)
    return redirect(url_for("calculator"))

# Route: Onderhoudskosten calculator
@app.route("/", methods=["GET", "POST"])
def calculator():
    if request.method == "POST":
        license_plate = request.form.get("license_plate")
        vehicle_data = fetch_vehicle_data(license_plate)

        if not vehicle_data:
            return render_template(
                "calculator.html", tasks=TASKS, error="Voertuiggegevens konden niet worden opgehaald. Controleer het kenteken."
            )

        # Opslaan van gegevens in de sessie
        session["vehicle_data"] = vehicle_data
        session["work_selections"] = {
            task: request.form.get(task) == "on" for task in TASKS
        }
        session["total_cost"] = calculate_cost(session["work_selections"])
        session["monthly_cost"] = round(session["total_cost"] / 12, 2)  # Bereken maandelijkse kosten

        return redirect(url_for("summary"))

    return render_template("calculator.html", tasks=TASKS, work_selections={})

# Route: Overzicht
@app.route("/summary", methods=["GET", "POST"])
def summary():
    if request.method == "POST":
        session["payment_option"] = request.form.get("payment_option")
        return redirect(url_for("customer_info"))

    vehicle_data = session.get("vehicle_data")
    if not vehicle_data:
        return redirect(url_for("calculator"))  # Terug naar calculator als data ontbreekt

    total_cost = session.get("total_cost")
    monthly_cost = session.get("monthly_cost")
    hourly_rate = session.get("hourly_rate", HOURLY_RATE)
    return render_template(
        "summary.html",
        vehicle_data=vehicle_data,
        total_cost=total_cost,
        monthly_cost=monthly_cost,
        hourly_rate=hourly_rate,
    )

# Route: Klantgegevens
@app.route("/customer-info", methods=["GET", "POST"])
def customer_info():
    vehicle_data = session.get("vehicle_data")
    if not vehicle_data:
        return redirect(url_for("calculator"))  # Terug naar calculator als data ontbreekt

    if request.method == "POST":
        session["customer_data"] = {
            "name": request.form.get("name"),
            "address": request.form.get("address"),
            "email": request.form.get("email"),  # Nieuw e-mailveld toegevoegd
            "iban": request.form.get("iban"),
            "signature": request.form.get("signature"),
        }
        return redirect(url_for("confirmation"))

    total_cost = session.get("total_cost")
    monthly_cost = session.get("monthly_cost")
    return render_template(
        "customer_info.html",
        vehicle_data=vehicle_data,
        payment_option=session.get("payment_option"),
        total_cost=total_cost,
        monthly_cost=monthly_cost,
    )

# Route: Bevestiging
@app.route("/confirmation", methods=["GET"])
def confirmation():
    customer_data = session.get("customer_data")
    if not customer_data:
        return redirect(url_for("customer_info"))  # Terug naar klantgegevens als data ontbreekt

    total_cost = session.get("total_cost", 0)
    monthly_cost = session.get("monthly_cost", 0)
    payment_option = session.get("payment_option", "Niet opgegeven")

    return render_template(
        "confirmation.html",
        customer_data=customer_data,
        total_cost=total_cost,
        monthly_cost=monthly_cost,
        payment_option=payment_option,
    )

# Start de Flask-app
if __name__ == "__main__":
    app.run(debug=True)
