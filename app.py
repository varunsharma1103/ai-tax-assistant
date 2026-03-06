from flask import Flask, render_template, request, session
import re

app = Flask(__name__)
app.secret_key = "super_secret_key"


# -----------------------
# Indian currency display
# -----------------------
def format_indian(amount):

    if amount >= 10000000:
        return f"₹{amount/10000000:.2f} Crore"

    if amount >= 100000:
        return f"₹{amount/100000:.2f} Lakh"

    return f"₹{amount:,.0f}"


# -----------------------
# Parse numbers
# -----------------------
def parse_amount(text):

    text = text.lower().replace(",", "")

    match = re.search(r"(\d+(\.\d+)?)", text)

    if not match:
        return 0

    number = float(match.group(1))

    if "crore" in text:
        return number * 10000000

    if "lakh" in text:
        return number * 100000

    return number


# -----------------------
# Tax calculator
# -----------------------
def calculate_tax(income, deductions):

    taxable = max(income - deductions, 0)

    old_tax = 0
    new_tax = 0

    # OLD REGIME
    if taxable > 250000:

        if taxable <= 500000:
            old_tax = (taxable - 250000) * 0.05

        elif taxable <= 1000000:
            old_tax = 12500 + (taxable - 500000) * 0.20

        else:
            old_tax = 112500 + (taxable - 1000000) * 0.30


    # NEW REGIME
    if taxable > 300000:

        if taxable <= 600000:
            new_tax = (taxable - 300000) * 0.05

        elif taxable <= 900000:
            new_tax = 15000 + (taxable - 600000) * 0.10

        elif taxable <= 1200000:
            new_tax = 45000 + (taxable - 900000) * 0.15

        elif taxable <= 1500000:
            new_tax = 90000 + (taxable - 1200000) * 0.20

        else:
            new_tax = 150000 + (taxable - 1500000) * 0.30


    # Rebate
    if taxable <= 500000:
        old_tax = 0

    if taxable <= 700000:
        new_tax = 0

    return taxable, old_tax, new_tax


# -----------------------
# ITR suggestion
# -----------------------
def suggest_itr(profession, income):

    if profession == "salaried" and income <= 5000000:
        return "ITR-1 (Sahaj)"

    if profession == "salaried" and income > 5000000:
        return "ITR-2"

    if profession in ["freelancer", "self employed", "business owner"]:
        return "ITR-3"

    return "ITR-2"


# -----------------------
# Home route
# -----------------------
@app.route("/", methods=["GET", "POST"])
def home():

    if request.method == "GET":

        session.clear()

        session["step"] = "profession"
        session["chat_history"] = []

        session["chat_history"].append({
            "role": "assistant",
            "content": "👋 Welcome to AI Tax Assistant.<br><br>Select your profession:"
        })


    if request.method == "POST":

        message = request.form["message"]

        session["chat_history"].append({
            "role": "user",
            "content": message
        })

        msg = message.lower()


        # -----------------------
        # FAQ HANDLER
        # -----------------------
        if "80c" in msg:

            response = """
📊 <b>Section 80C Deductions</b><br><br>

Maximum deduction: <b>₹1.5 Lakh</b>

Eligible investments:
• PPF  
• ELSS Mutual Funds  
• LIC Premium  
• EPF  
• Tax Saving FD
"""

        elif "itr filing" in msg:

            response = """
📄 <b>Steps to File ITR</b><br><br>

1️⃣ Login to Income Tax Portal  
2️⃣ Select correct ITR form  
3️⃣ Fill income details  
4️⃣ Add deductions  
5️⃣ Verify return using Aadhaar OTP
"""

        elif "new regime" in msg:

            response = """
📊 <b>New Tax Regime (FY 2025-26)</b>

0-3 Lakh → 0%  
3-6 Lakh → 5%  
6-9 Lakh → 10%  
9-12 Lakh → 15%  
12-15 Lakh → 20%  
Above 15 Lakh → 30%

✅ Rebate available up to ₹7 Lakh income.
"""

        elif "save tax" in msg:

            response = """
💡 <b>Best Tax Saving Options</b>

• Invest ₹1.5L under 80C  
• Health insurance deduction (80D)  
• NPS additional ₹50K  
• Home loan interest deduction  
• HRA exemption
"""

        else:

            step = session["step"]

            if step == "profession":

                session["profession"] = msg
                session["step"] = "age"

                response = "Great 👍 What is your age?"


            elif step == "age":

                if not message.isdigit():
                    response = "❌ Please enter age in numbers."

                else:

                    session["age"] = int(message)
                    session["step"] = "pan"

                    response = "Enter your PAN number (Example: ABCDE1234F)"


            elif step == "pan":

                pan = message.upper()

                if not re.match(r"[A-Z]{5}[0-9]{4}[A-Z]", pan):
                    response = "❌ Invalid PAN format."

                else:

                    session["pan"] = pan
                    session["step"] = "income"

                    response = "What is your annual income?"


            elif step == "income":

                income = parse_amount(message)

                if income == 0:
                    response = "❌ Please enter valid income."

                else:

                    session["income"] = income
                    session["step"] = "deductions"

                    response = "Enter your deductions (80C etc) or type 0."


            elif step == "deductions":

                deductions = parse_amount(message)

                income = session["income"]
                profession = session["profession"]

                taxable, old_tax, new_tax = calculate_tax(income, deductions)

                itr_form = suggest_itr(profession, income)

                better = "Old Regime" if old_tax < new_tax else "New Regime"
                savings = abs(old_tax - new_tax)

                response = f"""
💰 <b>Tax Summary</b><br>
Income: {format_indian(income)}<br>
Deductions: {format_indian(deductions)}<br>
Taxable Income: {format_indian(taxable)}<br><br>

📊 <b>Regime Comparison</b><br>
Old: {format_indian(old_tax)}<br>
New: {format_indian(new_tax)}<br><br>

✅ Recommendation: <b>{better}</b><br>
You save {format_indian(savings)}<br><br>

📄 Suggested ITR Form: <b>{itr_form}</b>
"""

                session["step"] = "complete"

            else:

                response = "Ask me about income tax, deductions or ITR filing."


        session["chat_history"].append({
            "role": "assistant",
            "content": response
        })


    return render_template(
        "chat.html",
        chat_history=session["chat_history"],
        step=session["step"]
    )


if __name__ == "__main__":
    app.run(debug=True)