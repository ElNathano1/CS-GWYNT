# CS-GWYNT API Documentation

## Overview

REST API for the CS-GWYNT Trading Card Game

## Base URL

```
http://localhost:8000/api/v1
```

## Endpoints

### Health Check

```
GET /health
```

### Game Management

- `POST /games` - Create a new game
- `GET /games/{game_id}` - Get game details
- `POST /games/{game_id}/join` - Join a game
- `POST /games/{game_id}/play` - Play a turn

### Player Management

- `POST /players` - Create player
- `GET /players/{player_id}` - Get player info
- `GET /players/{player_id}/deck` - Get player deck

### Card Management

- `GET /cards` - List all cards
- `GET /cards/{card_id}` - Get card details

## Authentication

(To be implemented)

## Response Format

All responses are in JSON format.

### Success Response

```json
{
  "status": "success",
  "data": {}
}
```

### Error Response

```json
{
  "status": "error",
  "message": "Error description"
}
```
