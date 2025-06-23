# Chat-App

## 🗨️ Python Chat Application
A simple yet functional client-server chat application written in Python using socket, threading, and tkinter. It supports:

User registration and login

Chat history saved to the server

Multiple simultaneous clients

GUI for clients with real-time message updates

Local user credential and history management

## 📦 Features
### ✅ Server
Accepts multiple client connections via multithreading

Auto-registers new users on first login

Validates returning users by password

Maintains persistent chat history per user (stored in ~/.chat_history.json)

Stores user credentials in ~/.chat_users.json

Broadcasts system messages like user joins/leaves

Forwards direct messages between users

### ✅ Client
GUI using tkinter (login, message view, and chat sidebar)

Message sending via button or Enter key

Real-time receive thread that parses messages with dual [recipient][sender] tags

Stores user credentials in ~/.chatclient_config.json

Allows new chat tabs to be opened manually via username entry

## Future Goals

Implementing end-to-end encryption using RSA

Creating applications using C++

Expanding to mobile applications

