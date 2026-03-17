from flask import Flask, render_template, request, session
import re
import os
from groq import Groq

app = Flask(__name__)
app.secret_key = "super_secret_key"

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# -----------------------
# AI RESPONSE
# -----------------------

def ai_reply(user_message, history):

    try:

        messages = [
            {
                "role": "system",
                "content": """
You are an AI assistant helping users understand Indian income tax.

Rules:
• Keep answers short
• Use bullet points where helpful
"""
            }
        ]

        for msg in history[-6:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        messages.append({
            "role": "user",
            "content": user_message
        })

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.2
        )

        return response.choices[0].message.content.replace("\n","<br>")

    except Exception:
        return "⚠️ AI service unavailable right now."


# -----------------------
# FORMAT INDIAN CURRENCY
# -----------------------

def format_indian(amount):

    if amount >= 10000000:
        return f"₹{amount/10000000:.2f} Crore"

    if amount >= 100000:
        return f"₹{amount/100000:.2f} Lakh"

    return f"₹{amount:,.0f}"


# -----------------------
# IMPROVED AMOUNT PARSER
# -----------------------

def parse_amount(text):

    text = text.lower().replace(",", "")

    total = 0

    crore_match = re.search(r'(\d+(\.\d+)?)\s*crore', text)
    lakh_match = re.search(r'(\d+(\.\d+)?)\s*lakh', text)
    thousand_match = re.search(r'(\d+(\.\d+)?)\s*thousand', text)

    if crore_match:
        total += float(crore_match.group(1)) * 10000000

    if lakh_match:
        total += float(lakh_match.group(1)) * 100000

    if thousand_match:
        total += float(thousand_match.group(1)) * 1000

    if total == 0:
        number_match = re.search(r'(\d+(\.\d+)?)', text)
        if number_match:
            total = float(number_match.group(1))

    return total if total != 0 else None


# -----------------------
# TAX CALCULATION
# -----------------------

def calculate_tax(income, deductions):

    taxable = max(income - deductions, 0)

    old_tax = 0
    new_tax = 0

    if taxable > 250000:

        if taxable <= 500000:
            old_tax = (taxable - 250000) * 0.05

        elif taxable <= 1000000:
            old_tax = 12500 + (taxable - 500000) * 0.20

        else:
            old_tax = 112500 + (taxable - 1000000) * 0.30


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


    if taxable <= 500000:
        old_tax = 0

    if taxable <= 700000:
        new_tax = 0

    return taxable, old_tax, new_tax


# -----------------------
# ITR SUGGESTION
# -----------------------

def suggest_itr(profession, income):

    if profession == "salaried" and income <= 5000000:
        return "ITR-1 (Sahaj)"

    if profession == "salaried" and income > 5000000:
        return "ITR-2"

    if profession in ["freelancer","self employed","business owner"]:
        return "ITR-3"

    return "ITR-2"


# -----------------------
# HOME ROUTE
# -----------------------

@app.route("/", methods=["GET","POST"])
def home():

    if request.method == "GET":

        session.clear()

        session["step"] = "profession"
        session["chat_history"] = []

        session["chat_history"].append({
            "role":"assistant",
            "content":"👋 Welcome to AI Tax Assistant.<br><br>Select your profession:"
        })


    if request.method == "POST":

        message = request.form["message"]
        msg = message.lower()

        session["chat_history"].append({
            "role":"user",
            "content":message
        })

        step = session["step"]


        # QUESTION DETECTION

        if any(word in msg for word in ["what","why","how","explain"]):

            ai_answer = ai_reply(message, session["chat_history"])

            followup = ""

            if step == "profession":
                followup = "<br><br>Please select your profession."

            elif step == "age":
                followup = "<br><br>Please enter your age."

            elif step == "pan":
                followup = "<br><br>Please enter your PAN number."

            elif step == "income":
                followup = "<br><br>Please enter your annual income."

            elif step == "deductions":
                followup = "<br><br>Please enter deductions amount or type 0."

            response = ai_answer + followup


        # PROFESSION STEP

        elif step == "profession":

            valid = ["salaried","freelancer","business owner","self employed"]

            if msg in valid:

                session["profession"] = msg
                session["step"] = "age"

                response = "Great 👍 What is your age?"

            else:

                ai_answer = ai_reply(message, session["chat_history"])
                response = ai_answer + "<br><br>Please select your profession."


        # AGE STEP

        elif step == "age":

            if not message.isdigit():

                ai_answer = ai_reply(message, session["chat_history"])
                response = ai_answer + "<br><br>Please enter your age in numbers."

            else:

                session["age"] = int(message)
                session["step"] = "pan"

                response = "Enter your PAN number (Example: ABCDE1234F)"


        # PAN STEP

        elif step == "pan":

            pan = message.upper()

            if not re.match(r"[A-Z]{5}[0-9]{4}[A-Z]", pan):

                ai_answer = ai_reply(message, session["chat_history"])
                response = ai_answer + "<br><br>Please enter valid PAN number."

            else:

                session["pan"] = pan
                session["step"] = "income"

                response = "What is your annual income?"


        # INCOME STEP

        elif step == "income":

            income = parse_amount(message)

            if income is None:

                ai_answer = ai_reply(message, session["chat_history"])
                response = ai_answer + "<br><br>Please enter valid income."

            else:

                session["income"] = income
                session["step"] = "deductions"

                response = "Enter your deductions (80C etc) or type 0."


        # DEDUCTIONS STEP

        elif step == "deductions":

            deductions = parse_amount(message)

            if deductions is None and message != "0":

                ai_answer = ai_reply(message, session["chat_history"])
                response = ai_answer + "<br><br>Please enter deduction amount or type 0."

            else:

                if deductions is None:
                    deductions = 0

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

✅ <b>Recommendation:</b> {better}<br>
You save {format_indian(savings)}<br><br>

📄 <b>Suggested ITR Form:</b> {itr_form}<br><br>

<hr>

✅ <b>Your tax calculation is complete.</b><br><br>

If you have more questions, feel free to ask about:<br>
• Tax deductions<br>
• ITR filing process<br>
• Choosing tax regime<br>
• Tax saving tips<br><br>

<b>How else can I assist you today?</b>
"""

                session["step"] = "complete"


        # AFTER COMPLETION

        else:

            response = ai_reply(message, session["chat_history"])


        session["chat_history"].append({
            "role":"assistant",
            "content":response
        })


    return render_template(
        "chat.html",
        chat_history=session["chat_history"],
        step=session["step"]
    )


if __name__ == "__main__":
    app.run(debug=True)
    
