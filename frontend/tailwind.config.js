/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#000000',
          sidebar: '#151515',
          header: '#151515',
          card: '#1E1E1E',
          surface: '#151515',
          border: '#2A2A2A',
        },
        gold: {
          DEFAULT: '#F2D04E',
          light: '#F8DF7B',
          dark: '#D4B337',
        },
        grey: {
          text: '#A0A0A0',
          muted: '#666666',
          border: '#333333',
        },
        status: {
          optimal: '#1B7A43',
          warning: '#F59E0B',
          alert: '#AC251D',
        }
      },
      fontFamily: {
        sans: ['"Hanken Grotesk"', 'sans-serif'],
        heading: ['Lexend', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
