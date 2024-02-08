// noinspection JSValidateTypes
/** @type {import('tailwindcss').Config} */
const defaultTheme = require('tailwindcss/defaultTheme')

// noinspection JSUnresolvedReference
module.exports = {
    content: [
        "./src/static/js/**/*.js",
        "./src/templates/**/*.html",
        "./src/templates/**/*.pt"
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter var', ...defaultTheme.fontFamily.sans],
            }
        }
    },
    plugins: [
        require('@tailwindcss/forms')
    ],
}

