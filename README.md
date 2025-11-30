# LangGraph Research Agent

A smart research assistant built with **LangGraph**, **FastAPI**, and **Qdrant**. This system integrates Retrieval-Augmented Generation (RAG) with real-time web search capabilities to provide accurate, context-aware answers. It features a self-reflective agentic workflow that autonomously decides between using internal knowledge bases or external web sources.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [License](#license)

## Overview

This project implements an autonomous agent using a state graph architecture. Unlike traditional linear RAG chains, this agent utilizes conditional logic to route queries, evaluate the quality of retrieved documents (Self-Correction), and fallback to web search when internal data is insufficient. It includes a frontend interface that visualizes the agent's "thinking process" in real-time.

## Key Features

- **Agentic Workflow:** Built on LangGraph to manage state and complex logic flows (Routing, Fallbacks, Loops).
- **Hybrid Information Retrieval:**
  - **RAG (Retrieval-Augmented Generation):** Searches user-uploaded PDFs using Qdrant vector database.
  - **Web Search:** Fallback mechanism using Tavily API for up-to-date information.
- **Intelligent Routing:** A semantic router classifies user intent to select the appropriate tool (RAG vs. Web vs. Direct Answer).
- **Self-Reflection (Judge Node):** An LLM-based evaluator checks if retrieved documents are sufficient to answer the query. If not, it triggers a web search.
- **Semantic Chunking:** Uses advanced text splitting based on semantic similarity rather than fixed character counts.
- **Transparent UI:** The frontend displays the execution trace (nodes visited, decisions made) alongside the final answer.

## System Architecture

The agent operates based on the following directed graph:

```mermaid
graph TD
    Start([User Query]) --> Router{Router Node}
    Router -- "Factual/Doc based" --> RAG[RAG Lookup]
    Router -- "Current events" --> Web[Web Search]
    Router -- "General chat" --> Answer[Generate Answer]
    
    RAG --> Judge{Judge Node}
    Judge -- "Sufficient" --> Answer
    Judge -- "Insufficient" --> Web
    
    Web --> Answer
    Answer --> End([Final Response])
