"""Static data for the demo seeder: menu, ingredients, names."""

# key: (name, base unit, cost per BASE unit, par level in base units for a busy branch)
# G = gram, ML = millilitre, PCS = piece
INGREDIENTS = {
    "chicken":     ("Chicken (boneless)", "G", 0.85, 18000),
    "chicken_bone": ("Chicken (with bone)", "G", 0.62, 20000),
    "beef":        ("Beef mince", "G", 1.40, 9000),
    "mutton":      ("Mutton", "G", 2.10, 6000),
    "rice":        ("Basmati rice", "G", 0.28, 15000),
    "flour":       ("Flour", "G", 0.09, 25000),
    "cheese":      ("Mozzarella cheese", "G", 1.30, 6000),
    "potato":      ("Potatoes", "G", 0.10, 14000),
    "tomato":      ("Tomatoes", "G", 0.12, 8000),
    "onion":       ("Onions", "G", 0.08, 8000),
    "gg_paste":    ("Ginger garlic paste", "G", 0.35, 3000),
    "spice":       ("Spice mix", "G", 0.90, 3000),
    "butter":      ("Butter", "G", 1.50, 2500),
    "lettuce":     ("Lettuce", "G", 0.20, 3000),
    "daal":        ("Daal mash", "G", 0.32, 5000),
    "yogurt":      ("Yogurt", "G", 0.20, 8000),
    "sugar":       ("Sugar", "G", 0.14, 5000),
    "tea":         ("Tea leaves", "G", 1.20, 1000),
    "pepperoni":   ("Pepperoni", "G", 1.80, 2500),
    "oil":         ("Cooking oil", "ML", 0.45, 25000),
    "milk":        ("Milk", "ML", 0.15, 20000),
    "mayo":        ("Mayonnaise", "ML", 0.40, 5000),
    "ketchup":     ("Ketchup", "ML", 0.20, 5000),
    "cream":       ("Cream", "ML", 0.50, 4000),
    "mint":        ("Mint syrup", "ML", 0.30, 3000),
    "bun":         ("Burger bun", "PCS", 25, 120),
    "cola":        ("Soft drink can", "PCS", 70, 150),
    "egg":         ("Eggs", "PCS", 35, 100),
    "pizza_base":  ("Pizza base", "PCS", 90, 60),
    "jamun":       ("Gulab jamun (ready)", "PCS", 30, 80),
}

# in-house preparations: key -> (name, {ingredient: grams/ml/pcs per ONE piece})
PREPARED = {
    "zinger_patty": ("Zinger patty", {"chicken": 110, "flour": 15, "spice": 5, "oil": 20}),
    "beef_patty":   ("Beef smash patty", {"beef": 120, "onion": 10, "spice": 3}),
    "naan_ball":    ("Naan dough ball", {"flour": 90, "yogurt": 15, "oil": 5}),
}

# category, dish, popularity weight, [(variant, price, {ingredient_or_prepared: qty} or None)]
# a recipe of None means "no recipe yet" (shows the owner's nudge in reports)
MENU = [
    ("Burgers", "Zinger Burger", 10, [
        ("Regular", 450, {"bun": 1, "zinger_patty": 1, "mayo": 15, "lettuce": 15, "cheese": 10}),
        ("Double", 650, {"bun": 1, "zinger_patty": 2, "mayo": 20, "lettuce": 20, "cheese": 20})]),
    ("Burgers", "Beef Smash Burger", 6, [
        ("Regular", 550, {"bun": 1, "beef_patty": 1, "cheese": 15, "ketchup": 10, "onion": 10}),
        ("Double", 800, {"bun": 1, "beef_patty": 2, "cheese": 30, "ketchup": 15, "onion": 15})]),
    ("Burgers", "Chicken Cheese Burger", 5, [
        ("Regular", 420, {"bun": 1, "zinger_patty": 1, "cheese": 25, "mayo": 10})]),
    ("BBQ", "Chicken Tikka", 9, [
        ("Quarter", 520, {"chicken_bone": 250, "yogurt": 40, "spice": 12, "gg_paste": 10}),
        ("Half", 980, {"chicken_bone": 500, "yogurt": 80, "spice": 24, "gg_paste": 20})]),
    ("BBQ", "Seekh Kabab (4 pcs)", 6, [
        ("Regular", 480, {"beef": 220, "onion": 25, "spice": 10, "oil": 10})]),
    ("BBQ", "Malai Boti (6 pcs)", 5, [
        ("Regular", 690, {"chicken": 260, "cream": 40, "yogurt": 30, "spice": 8})]),
    ("Karahi", "Chicken Karahi", 8, [
        ("Half", 1350, {"chicken_bone": 450, "tomato": 200, "gg_paste": 25, "oil": 60, "spice": 15}),
        ("Full", 2450, {"chicken_bone": 900, "tomato": 380, "gg_paste": 50, "oil": 110, "spice": 28})]),
    ("Karahi", "Mutton Karahi", 4, [
        ("Half", 2200, {"mutton": 450, "tomato": 180, "gg_paste": 25, "oil": 70, "spice": 15}),
        ("Full", 4200, {"mutton": 900, "tomato": 350, "gg_paste": 50, "oil": 130, "spice": 28})]),
    ("Karahi", "Daal Mash", 3, [
        ("Regular", 420, {"daal": 150, "butter": 20, "onion": 30, "spice": 5})]),
    ("Rice & Bread", "Chicken Biryani", 9, [
        ("Regular", 480, {"rice": 220, "chicken_bone": 180, "onion": 40, "oil": 30, "spice": 10, "yogurt": 30})]),
    ("Rice & Bread", "Plain Naan", 12, [("Regular", 40, {"naan_ball": 1})]),
    ("Rice & Bread", "Garlic Naan", 6, [("Regular", 80, {"naan_ball": 1, "butter": 8, "gg_paste": 5})]),
    ("Pizza", "Fajita Pizza", 6, [
        ("Medium", 1100, {"pizza_base": 1, "cheese": 120, "chicken": 100, "tomato": 40, "onion": 25}),
        ("Large", 1650, {"pizza_base": 1, "cheese": 200, "chicken": 160, "tomato": 60, "onion": 40})]),
    ("Pizza", "Pepperoni Pizza", 5, [
        ("Medium", 1200, {"pizza_base": 1, "cheese": 130, "pepperoni": 60, "tomato": 40}),
        ("Large", 1800, {"pizza_base": 1, "cheese": 210, "pepperoni": 100, "tomato": 60})]),
    ("Sides", "French Fries", 9, [
        ("Regular", 250, {"potato": 220, "oil": 40}),
        ("Large", 380, {"potato": 350, "oil": 60})]),
    ("Sides", "Raita", 4, [("Regular", 80, None)]),
    ("Sides", "Fresh Salad", 3, [("Regular", 100, {"lettuce": 60, "tomato": 50, "onion": 30})]),
    ("Drinks", "Soft Drink", 11, [("Regular", 120, {"cola": 1})]),
    ("Drinks", "Mint Margarita", 7, [("Regular", 250, {"mint": 40, "yogurt": 20, "sugar": 15})]),
    ("Drinks", "Sweet Lassi", 5, [("Regular", 220, {"yogurt": 200, "sugar": 30, "milk": 80})]),
    ("Drinks", "Doodh Patti Chai", 8, [("Regular", 100, {"milk": 150, "tea": 4, "sugar": 12})]),
    ("Desserts", "Kheer", 3, [("Regular", 220, None)]),
    ("Desserts", "Gulab Jamun (2 pcs)", 3, [("Regular", 180, {"jamun": 2})]),
]

FIRST = ["Ali", "Ahmed", "Usman", "Hassan", "Bilal", "Hamza", "Zain", "Saad", "Fahad", "Imran", "Kamran", "Asad", "Faisal", "Talha",
         "Ayesha", "Fatima", "Sana", "Hina", "Maryam", "Zainab", "Nida", "Amna", "Iqra", "Sara", "Rabia", "Mehwish", "Khadija", "Laiba"]
LAST = ["Khan", "Ahmed", "Malik", "Sheikh", "Butt", "Raza", "Qureshi", "Siddiqui", "Chaudhry", "Hussain", "Iqbal", "Ansari", "Mirza", "Baig", "Farooqi"]
AREAS = ["DHA Phase 5", "Clifton Block 4", "Gulshan-e-Iqbal", "PECHS", "Gulberg III", "Model Town", "Johar Town", "F-7 Markaz", "G-9", "Bahria Town", "Saddar", "North Nazimabad"]
CANCEL_REASONS = ["Customer left / changed mind", "Wrong order entered", "Item not available", "Duplicate order", "Customer waited too long", "Kitchen problem"]
REFUND_REASONS = ["Cold food", "Wrong item served", "Item missing from order", "Customer complaint", "Overcharged"]
EXPENSES = [("vegetables", "Vegetables from mandi", (800, 3500)), ("fuel", "Charcoal", (600, 1800)), ("gas", "Gas cylinder", (2200, 4500)),
            ("cleaning", "Cleaning supplies", (300, 1200)), ("ice", "Ice", (200, 700)), ("repairs", "Minor repair", (500, 2500)),
            ("packaging", "Takeaway boxes", (700, 2500))]
