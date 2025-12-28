/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	darkMode: 'class',
	theme: {
		extend: {
			fontFamily: {
				sans: [
					'-apple-system',
					'BlinkMacSystemFont',
					'SF Pro Display',
					'SF Pro Text',
					'Segoe UI',
					'Roboto',
					'Helvetica Neue',
					'Arial',
					'sans-serif'
				],
				mono: [
					'SF Mono',
					'Monaco',
					'Menlo',
					'Consolas',
					'Liberation Mono',
					'Courier New',
					'monospace'
				]
			},
			colors: {
				// Apple-inspired dark mode palette
				apple: {
					bg: {
						primary: '#000000',
						secondary: '#1c1c1e',
						tertiary: '#2c2c2e',
						elevated: '#3a3a3c'
					},
					text: {
						primary: '#ffffff',
						secondary: '#8e8e93',
						tertiary: '#636366',
						quaternary: '#48484a'
					},
					border: {
						DEFAULT: '#3a3a3c',
						subtle: '#2c2c2e',
						strong: '#48484a'
					},
					blue: {
						DEFAULT: '#0a84ff',
						hover: '#409cff',
						pressed: '#0077ed'
					},
					green: {
						DEFAULT: '#30d158',
						hover: '#34c759',
						muted: '#30d15833'
					},
					orange: {
						DEFAULT: '#ff9f0a',
						hover: '#ffb340',
						muted: '#ff9f0a33'
					},
					red: {
						DEFAULT: '#ff453a',
						hover: '#ff6961',
						muted: '#ff453a33'
					},
					purple: {
						DEFAULT: '#bf5af2',
						hover: '#da8fff',
						muted: '#bf5af233'
					},
					cyan: {
						DEFAULT: '#64d2ff',
						hover: '#70d7ff',
						muted: '#64d2ff33'
					},
					pink: {
						DEFAULT: '#ff2d55',
						hover: '#ff4f6d'
					},
					indigo: {
						DEFAULT: '#5e5ce6',
						hover: '#7a78ff'
					}
				}
			},
			borderRadius: {
				'apple-sm': '6px',
				'apple': '10px',
				'apple-md': '12px',
				'apple-lg': '16px',
				'apple-xl': '20px'
			},
			boxShadow: {
				'apple-sm': '0 1px 3px rgba(0, 0, 0, 0.3)',
				'apple': '0 2px 10px rgba(0, 0, 0, 0.3)',
				'apple-lg': '0 4px 20px rgba(0, 0, 0, 0.4)',
				'apple-glow': '0 0 20px rgba(10, 132, 255, 0.3)'
			},
			backdropBlur: {
				'apple': '20px'
			},
			transitionDuration: {
				'apple': '180ms'
			},
			transitionTimingFunction: {
				'apple': 'cubic-bezier(0.25, 0.1, 0.25, 1)'
			},
			animation: {
				'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
				'fade-in': 'fadeIn 0.2s ease-out',
				'slide-up': 'slideUp 0.2s ease-out'
			},
			keyframes: {
				fadeIn: {
					'0%': { opacity: '0' },
					'100%': { opacity: '1' }
				},
				slideUp: {
					'0%': { opacity: '0', transform: 'translateY(10px)' },
					'100%': { opacity: '1', transform: 'translateY(0)' }
				}
			}
		}
	},
	plugins: []
};
