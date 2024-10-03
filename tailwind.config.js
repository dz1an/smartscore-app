/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './templates/**/*.html',
    './node_modules/flowbite/**/*.js'
  ],
  theme: {
    screens: {
      sm: '480px',
      md: '768px',
      lg: '976px',
      xl: '1440px',
    },
    extend: {
      colors: {
        'custom-blue': '#1fb6ff',
        'custom-purple': '#7e5bef',
        'custom-pink': '#ff49db',
        'custom-orange': '#ff7849',
        'custom-green': '#13ce66',
        'custom-yellow': '#ffc82c',
        'custom-gray-dark': '#273444',
        'custom-gray': '#8492a6',
        'custom-gray-light': '#d3dce6',
      },
      fontFamily: {
        sans: ['Graphik', 'sans-serif'],
        serif: ['Merriweather', 'serif'],
      },
      borderRadius: {
        '4xl': '2rem',
      },
      spacing: {
        '128': '32rem',
        '144': '36rem',
      },
    },
  },
  plugins: [require('flowbite/plugin')],
  safelist: [
    {
      pattern: /^(?!.*\b(block|inline-block|inline)\b).*\bvertical-align-/,
    }
  ]
}

// postcss.config.js
module.exports = {
  plugins: [
    require('tailwindcss'),
    require('autoprefixer')({
      // Add specific browser versions if needed
      // browsers: ['last 2 versions', '> 5%']
    }),
  ]
}