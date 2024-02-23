/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./base/jinja2/**/*.{html,js}"],
  theme: {
    extend: {},
  },
  plugins: [
    require("@tailwindcss/forms"),
  ],
}

