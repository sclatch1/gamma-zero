const pieces = {
  k: {
    paths: [
      <path
        key="1"
        d="M50 12v18M40 21h20"
        stroke="currentColor"
        strokeWidth="5"
        strokeLinecap="round"
      />,
      <path
        key="2"
        d="M30 35h40l-5 12H35z"
        fill="currentColor"
      />,
      <path
        key="3"
        d="M35 47h30l8 35H27z"
        fill="currentColor"
      />,
      <path
        key="4"
        d="M22 82h56"
        stroke="currentColor"
        strokeWidth="7"
        strokeLinecap="round"
      />,
      <path
        key="5"
        d="M17 91h66"
        stroke="currentColor"
        strokeWidth="9"
        strokeLinecap="round"
      />,
    ],
  },

  q: {
    paths: [
      <circle key="1" cx="22" cy="22" r="7" fill="currentColor" />,
      <circle key="2" cx="50" cy="15" r="7" fill="currentColor" />,
      <circle key="3" cx="78" cy="22" r="7" fill="currentColor" />,
      <path
        key="4"
        d="M22 29l10 40h36l10-40-18 18-10-25-10 25z"
        fill="currentColor"
      />,
      <path
        key="5"
        d="M30 69h40"
        stroke="currentColor"
        strokeWidth="6"
      />,
      <path
        key="6"
        d="M24 78h52"
        stroke="currentColor"
        strokeWidth="9"
        strokeLinecap="round"
      />,
      <path
        key="7"
        d="M18 90h64"
        stroke="currentColor"
        strokeWidth="9"
        strokeLinecap="round"
      />,
    ],
  },

  r: {
    paths: [
      <path
        key="1"
        d="M27 20h46v16H27z"
        fill="currentColor"
      />,
      <path
        key="2"
        d="M32 36h36v35H32z"
        fill="currentColor"
      />,
      <path
        key="3"
        d="M25 71h50"
        stroke="currentColor"
        strokeWidth="7"
      />,
      <path
        key="4"
        d="M18 84h64"
        stroke="currentColor"
        strokeWidth="9"
        strokeLinecap="round"
      />,
      <path
        key="5"
        d="M14 93h72"
        stroke="currentColor"
        strokeWidth="8"
        strokeLinecap="round"
      />,
    ],
  },

  b: {
    paths: [
      <path
        key="1"
        d="M50 15c-10 12-17 21-17 31 0 8 5 13 10 17L28 72h44L57 63c5-4 10-9 10-17 0-10-7-19-17-31z"
        fill="currentColor"
      />,
      <path
        key="2"
        d="M43 24l14 30"
        stroke="#eee"
        strokeWidth="4"
      />,
      <path
        key="3"
        d="M28 72h44"
        stroke="currentColor"
        strokeWidth="7"
      />,
      <path
        key="4"
        d="M20 84h60"
        stroke="currentColor"
        strokeWidth="9"
        strokeLinecap="round"
      />,
      <path
        key="5"
        d="M15 93h70"
        stroke="currentColor"
        strokeWidth="8"
        strokeLinecap="round"
      />,
    ],
  },

  n: {
    paths: [
      <path
        key="1"
        d="M30 84c5-18 6-32 3-45l-7-24h22l10 14c12-5 24 1 27 13 3 12-4 21-14 24l-7 18z"
        fill="currentColor"
      />,
      <path
        key="2"
        d="M49 31c7 4 13 9 17 16"
        fill="none"
        stroke="#eee"
        strokeWidth="4"
      />,
      <path
        key="3"
        d="M23 84h54"
        stroke="currentColor"
        strokeWidth="9"
        strokeLinecap="round"
      />,
      <path
        key="4"
        d="M17 93h66"
        stroke="currentColor"
        strokeWidth="8"
        strokeLinecap="round"
      />,
    ],
  },

  p: {
    paths: [
      <circle
        key="1"
        cx="50"
        cy="30"
        r="17"
        fill="currentColor"
      />,
      <path
        key="2"
        d="M35 47h30l9 30H26z"
        fill="currentColor"
      />,
      <path
        key="3"
        d="M25 77h50"
        stroke="currentColor"
        strokeWidth="7"
      />,
      <path
        key="4"
        d="M18 89h64"
        stroke="currentColor"
        strokeWidth="9"
        strokeLinecap="round"
      />,
    ],
  },
}

export default function Piece({ type }) {
  if (!type) {
    return null
  }

  const piece = pieces[type.toLowerCase()]

  if (!piece) {
    return null
  }

  const isWhite = type === type.toUpperCase()

  return (
    <svg
      className={`piece ${isWhite ? 'white-piece' : 'black-piece'}`}
      viewBox="0 0 100 100"
      aria-hidden="true"
    >
      {piece.paths}
    </svg>
  )
}