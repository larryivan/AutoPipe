/** @type {import('tailwindcss').Config} */
export default {
    content: [
      "./index.html",
      "./src/**/*.{vue,js,ts,jsx,tsx}", //确保这里包含了你的Vue文件路径
    ],
    darkMode: 'class',
    theme: {
      extend: {},
    },
    plugins: [],
  }