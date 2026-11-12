// Brews & Blessings menu data. Edit prices and items here.
// Each drink has prices for Classic, Grandeur and (if it has a hot version) Hot.

const SIZES = ["Classic", "Grandeur", "Hot"];
const SHOTS = ["No Shot", "1 Shot", "2 Shots"];
const ICE = ["Regular ice", "Less ice", "No ice", "Extra ice"];
const SWEETNESS = [
  { value: "0%", label: "0%" },
  { value: "20%", label: "20%" },
  { value: "50%", label: "50%" },
  { value: "70%", label: "70%" },
  { value: "100%", label: "100% Regular" }
];

// espresso: true = the Espresso Shot option is shown for this category
const CATEGORIES = [
  { id: "coffee",     label: "Coffee",          espresso: true },
  { id: "premium",    label: "Premium Coffee",  espresso: true },
  { id: "seasalt",    label: "Sea Salt Series", espresso: true },
  { id: "matcha",     label: "Matcha Series",   espresso: false },
  { id: "ube",        label: "Ube Series",      espresso: false },
  { id: "noncoffee",  label: "Non-Coffee",      espresso: false },
  { id: "refreshers", label: "Refreshers",      espresso: false }
];

function item(cat, name, classic, grandeur, hot) {
  const prices = { Classic: classic, Grandeur: grandeur };
  if (hot != null) prices.Hot = hot;
  return { cat, name, prices };
}

const MENU = [
  // Coffee
  item("coffee", "Americano", 80, 110, 60),
  item("coffee", "Cafe Latte", 120, 150, 110),
  item("coffee", "Caramel Latte", 120, 150, 115),
  item("coffee", "Caramel Macchiato", 130, 160, 125),
  item("coffee", "Hazelnut Latte", 120, 150, 115),
  item("coffee", "Mocha Latte", 130, 160, 125),
  item("coffee", "Salted Caramel Latte", 120, 150, 115),
  item("coffee", "Spanish Latte", 130, 160, 125),
  item("coffee", "White Mocha Latte", 130, 160, 125),
  item("coffee", "Tres Leche Latte", 130, 160, 125),

  // Premium Coffee
  item("premium", "Caramelized Mocha", 130, 160, 125),
  item("premium", "Biscoff Latte", 165, 205, 160),

  // Sea Salt Series
  item("seasalt", "Sea salt Latte", 150, 170, 145),
  item("seasalt", "Sea salt Spanish Latte", 160, 180, 155),
  item("seasalt", "Sea salt Ube Milk", 150, 170, 145),
  item("seasalt", "Sea salt Matcha", 150, 170, 145),
  item("seasalt", "Sea salt Dark Choco", 150, 170, 145),
  item("seasalt", "Sea salt Biscoff Milk", 190, 210, 185),

  // Matcha Series
  item("matcha", "Dirty Matcha", 130, 160, 125),
  item("matcha", "Strawberry Matcha", 120, 150, 115),
  item("matcha", "Matcha Milk", 120, 150, 115),

  // Ube Series
  item("ube", "Ube Latte", 130, 160, 125),
  item("ube", "Ube Matcha", 120, 150, 115),
  item("ube", "Ube Milk", 120, 150, 115),

  // Non-Coffee
  item("noncoffee", "Blueberry Milk", 110, 140, 105),
  item("noncoffee", "Caramel Milk", 110, 140, 105),
  item("noncoffee", "Chocolate Milk", 110, 140, 105),
  item("noncoffee", "Dark Choco Lava", 110, 140, 105),
  item("noncoffee", "Biscoff Milk", 150, 180, 145),
  item("noncoffee", "Mango Milk", 110, 140, 105),
  item("noncoffee", "Strawberry Milk", 110, 140, 105),
  item("noncoffee", "Oreo Milk", 110, 140, 105),
  item("noncoffee", "Strawberry Cocoa", 120, 150, 115),
  item("noncoffee", "Milky Berry Oreo", 120, 150, 115),

  // Refreshers (Classic and Grandeur only)
  item("refreshers", "Blueberry Fizz", 69, 89),
  item("refreshers", "Green Apple Fizz", 69, 89),
  item("refreshers", "Lychee Fizz", 69, 89),
  item("refreshers", "Mango Fizz", 69, 89),
  item("refreshers", "Strawberry Fizz", 69, 89),
  item("refreshers", "Passion Fruit Fizz", 69, 89),
  item("refreshers", "Mango Passion", 110, 140),
  item("refreshers", "Paradise Coconut", 140, 170),
  item("refreshers", "Pink Berry Drink", 140, 170)
];
