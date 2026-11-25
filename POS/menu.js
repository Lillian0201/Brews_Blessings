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
  { id: "coffee",     label: "Coffee",     espresso: true },
  { id: "noncoffee",  label: "Non-Coffee", espresso: false },
  { id: "refreshers", label: "Refreshers", espresso: false }
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
  item("coffee", "Caramelized Mocha", 130, 160, 125),
  item("coffee", "Dirty Matcha", 130, 160, 125),
  item("coffee", "Hazelnut Latte", 120, 150, 115),
  item("coffee", "Salted Caramel Latte", 120, 150, 115),
  item("coffee", "Spanish Latte", 130, 160, 125),
  item("coffee", "Tres Leche Latte", 130, 160, 125),
  item("coffee", "White Mocha Latte", 130, 160, 125),
  item("coffee", "Biscoff Latte", 165, 205, 160),

  // Non-Coffee
  item("noncoffee", "Blueberry Milk", 110, 140, 105),
  item("noncoffee", "Caramel Milk", 110, 140, 105),
  item("noncoffee", "Chocolate Milk", 110, 140, 105),
  item("noncoffee", "Strawberry Milk", 110, 140, 105),
  item("noncoffee", "Oreo Milk", 110, 140, 105),
  item("noncoffee", "Matcha Milk", 120, 150, 115),
  item("noncoffee", "Strawberry Matcha", 120, 150, 115),
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
