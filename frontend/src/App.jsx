import { useEffect, useState } from 'react'
import './App.css'
import Piece from './Piece'

const API_URL = 'http://localhost:8000'

const pieceSymbols = {
  1: '♔',
  2: '♕',
  3: '♖',
  4: '♗',
  5: '♘',
  6: '♙',

  '-1': '♚',
  '-2': '♛',
  '-3': '♜',
  '-4': '♝',
  '-5': '♞',
  '-6': '♟',
}

function squareName(row, col) {
  return `${String.fromCharCode(97 + col)}${row + 1}`
}

function moveName(move) {
  return `${squareName(...move.from)} → ${squareName(...move.to)}`
}

function App() {
  const [game, setGame] = useState(null)
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadGame()
  }, [])

  async function loadGame() {
    try {
      setLoading(true)

      const response = await fetch(`${API_URL}/game`)

      if (!response.ok) {
        throw new Error('Failed to load game')
      }

      const data = await response.json()

      setGame(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function getMovesFromSquare(row, col) {
    if (!game) {
      return []
    }

    return game.legal_moves.filter(
      (move) =>
        move.from[0] === row &&
        move.from[1] === col
    )
  }

  function isLegalDestination(row, col) {
    if (!selected || !game) {
      return false
    }

    return game.legal_moves.some(
      (move) =>
        move.from[0] === selected[0] &&
        move.from[1] === selected[1] &&
        move.to[0] === row &&
        move.to[1] === col
    )
  }

  function handleSquareClick(row, col) {
    if (!game || game.game_over || game.turn !== 'w') {
      return
    }

    const piece = game.board[row][col]

    if (!selected) {
      if (
        piece > 0 &&
        getMovesFromSquare(row, col).length > 0
      ) {
        setSelected([row, col])
      }

      return
    }

    if (selected[0] === row && selected[1] === col) {
      setSelected(null)
      return
    }

    if (
      piece > 0 &&
      getMovesFromSquare(row, col).length > 0
    ) {
      setSelected([row, col])
      return
    }

    const legalMove = game.legal_moves.find(
      (move) =>
        move.from[0] === selected[0] &&
        move.from[1] === selected[1] &&
        move.to[0] === row &&
        move.to[1] === col
    )

    if (!legalMove) {
      return
    }

    // Promotion
    if (legalMove.promo !== null) {
      makeMove(
        selected[0],
        selected[1],
        row,
        col,
        legalMove.promo
      )
    } else {
      makeMove(
        selected[0],
        selected[1],
        row,
        col,
        null
      )
    }
  }
  async function makeMove(
  fromRow,
  fromCol,
  toRow,
  toCol
) {
  try {
    setLoading(true)
    setSelected(null)
    setError(null)

    const response = await fetch(
      `${API_URL}/game/move`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          from_row: fromRow,
          from_col: fromCol,
          to_row: toRow,
          to_col: toCol,
        }),
      }
    )

    const data = await response.json()

    if (data.error) {
      throw new Error(data.error)
    }

    setGame(data)
  } catch (err) {
    setError(err.message)
  } finally {
    setLoading(false)
  }
}

  async function resetGame() {
    try {
      setSelected(null)
      setLoading(true)

      const response = await fetch(
        `${API_URL}/game/reset`,
        {
          method: 'POST',
        }
      )

      const data = await response.json()

      setGame(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading && !game) {
    return (
      <div className="app">
        <h1>Gamma Zero</h1>
        <p>Loading game...</p>
      </div>
    )
  }

  if (error && !game) {
    return (
      <div className="app">
        <h1>Gamma Zero</h1>

        <p className="error">
          {error}
        </p>

        <p>
          Make sure the FastAPI backend is running.
        </p>
      </div>
    )
  }

  return (
    <div className="app">
      <header>
        <h1>Gamma Zero</h1>
        <p>Gardner Minichess</p>
      </header>

      <main className="game">

        <div>
          <div className="board">

            {[...game.board].reverse().map((row, displayRowIndex) =>
              row.map((piece, colIndex) => {
                const rowIndex = 4 - displayRowIndex

                const isDark =
                  (displayRowIndex + colIndex) % 2 === 1

                const isSelected =
                  selected &&
                  selected[0] === rowIndex &&
                  selected[1] === colIndex

                const isDestination =
                  isLegalDestination(
                    rowIndex,
                    colIndex
                  )

                return (
                  <button
                    key={`${rowIndex}-${colIndex}`}
                    className={`
                      square
                      ${isDark ? 'dark' : 'light'}
                      ${isSelected ? 'selected' : ''}
                      ${isDestination ? 'destination' : ''}
                    `}
                    onClick={() =>
                      handleSquareClick(
                        rowIndex,
                        colIndex
                      )
                    }
                  >
                    <Piece
                      type={
                        piece === 0
                          ? null
                          : piece > 0
                            ? ['K', 'Q', 'R', 'B', 'N', 'P'][piece - 1]
                            : ['k', 'q', 'r', 'b', 'n', 'p'][-piece - 1]
                          }
                    />
                  </button>
                )
              })
        )}

          </div>

          <div className="coordinates">
            <span>a</span>
            <span>b</span>
            <span>c</span>
            <span>d</span>
            <span>e</span>
          </div>
        </div>

        <div className="side-panel">

          <h2>
            {game.game_over
              ? 'Game Over'
              : game.turn === 'w'
                ? 'Your turn'
                : 'Black to move'}
          </h2>

          <p>
            {game.game_over
              ? game.result === 1
                ? 'White wins'
                : game.result === -1
                  ? 'Black wins'
                  : 'Draw'
              : game.turn === 'w'
                ? 'White'
                : 'Black'}
          </p>

          <div className="moves">
            <h3>Legal moves</h3>

            {game.legal_moves.map(
              (move, index) => (
                <button
                  key={index}
                  onClick={() =>
                    makeMove(
                      move.from[0],
                      move.from[1],
                      move.to[0],
                      move.to[1]
                    )
                  }
                >
                  {index + 1}. {moveName(move)}
                </button>
              )
            )}
          </div>

          <button
            className="reset"
            onClick={resetGame}
          >
            New Game
          </button>

          {loading && (
            <p className="thinking">
              Updating...
            </p>
          )}

          {error && (
            <p className="error">
              {error}
            </p>
          )}

        </div>

      </main>
    </div>
  )
}

export default App