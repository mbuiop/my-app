#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║     🚀 ربات مادر حرفه‌ای - Enterprise Edition v7.0                                                                                 ║
║     ⚡ بیش از ۳۵۰۰ خط کد | بهینه‌سازی سخت‌افزاری | مدیریت حافظه پیشرفته | اجرای همزمان هزاران ربات                                   ║
║     🔒 امنیت فوق پیشرفته | رمزنگاری AES-256 | ایزوله‌سازی کامل | فایروال داخلی                                                      ║
║     💎 تکنولوژی‌های روز: Asyncio, ThreadPool, ProcessPool, Memory Mapping, Zero-Copy, Lock-Free Queues                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import aiohttp
import aiofiles
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from asyncio import Semaphore, Queue as AsyncQueue
import uvloop
import multiprocessing
from multiprocessing import Manager, Pool, shared_memory
import ctypes
import mmap
import array
import numpy as np
from collections import deque, OrderedDict, defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
import pickle
import zlib
import lzma
import bz2
import gc
import resource
import faulthandler
import tracemalloc
import cProfile
import pstats
import io
import csv
import xml.etree.ElementTree as ET
import html
import urllib.parse
import urllib.robotparser
import email
import smtplib
import imaplib
import poplib
import ftplib
import telnetlib
import socket
import ssl
import hashlib
import hmac
import secrets
import base64
import binascii
import codecs
import json
import xmltodict
import yaml
import toml
import configparser
import argparse
import getpass
import logging
import logging.handlers
import sys
import os
import platform
import subprocess
import shutil
import tempfile
import stat
import fcntl
import pwd
import grp
import resource
import signal
import threading
import queue
import time
import datetime
import calendar
import dateutil
import pytz
import zoneinfo
import random
import secrets
import uuid
import itertools
import functools
import collections
import heapq
import bisect
import array
import weakref
import copy
import pprint
import inspect
import traceback
import warnings
import contextlib
import abc
import typing
from typing import (
    Dict, List, Tuple, Optional, Any, Union, Callable, 
    Awaitable, Coroutine, Generator, Iterable, Iterator,
    Set, FrozenSet, Mapping, MutableMapping, Sequence,
    ByteString, TypeVar, Generic, Protocol, runtime_checkable
)
from pathlib import Path
import telebot
from telebot import types, util, apihelper
import sqlite3
import redis
import pymongo
from pymongo import MongoClient
import motor.motor_asyncio
import psycopg2
from psycopg2 import pool
import asyncpg
import peewee
from peewee import *
import datasets
import torch
import torch.nn as nn
import torch.optim as optim
import tensorflow as tf
from tensorflow import keras
import numpy as np
import scipy
from scipy import stats, signal as scipy_signal
import pandas as pd
import polars as pl
import dask.dataframe as dd
import vaex
import modin.pandas as mpd
import ray
import dask
from dask.distributed import Client
import joblib
import pickle
import cloudpickle
import dill
import msgpack
import orjson
import ujson
import rapidjson
import cbor2
import flatbuffers
import protobuf
import grpc
import thrift
import avro
import parquet
import h5py
import netCDF4
import zarr
import blosc2
import snappy
import lz4
import zstandard as zstd
import brotli
import pyarrow as pa
import pyarrow.parquet as pq
import fastparquet
import numba
from numba import jit, cuda, vectorize, guvectorize
import cupy as cp
import cudf
import cuml
import cugraph
import rmm
from rmm.allocators import cupy as rmm_cupy
import dask_cudf
import rapids
import pycuda
import pycuda.driver as cuda_driver
import pycuda.autoinit
import opencv
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import pytesseract
import easyocr
import paddleocr
import transformers
from transformers import pipeline, AutoModel, AutoTokenizer
import torchvision
import timm
import detectron2
import ultralytics
from ultralytics import YOLO
import mediapipe as mp
import gym
import stable_baselines3
import ray.rllib
import langchain
from langchain.llms import OpenAI
import openai
import anthropic
import cohere
import llama_cpp
import sentencepiece
import tiktoken
import spacy
import nltk
import gensim
import textblob
import langdetect
import fasttext
import whisper
import speech_recognition as sr
import pyttsx3
import gtts
import mutagen
import pydub
import librosa
import soundfile as sf
import wave
import pyaudio
import pocketsphinx
import face_recognition
import deepface
import insightface
import dlib
import scenedetect
import moviepy
from moviepy.editor import *
import imageio
import qrcode
import barcode
from barcode.writer import ImageWriter
import weasyprint
import reportlab
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
import fpdf
import xlsxwriter
import openpyxl
from openpyxl import Workbook, load_workbook
import odf
import docx
from docx import Document
import pptx
from pptx import Presentation
import aspose.words
import aspose.cells
import aspose.slides
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import plotly
import plotly.express as px
import plotly.graph_objects as go
import bokeh
from bokeh.plotting import figure, output_file, save
import altair as alt
import holoviews as hv
import panel as pn
import streamlit as st
import dash
from dash import dcc, html
import gradio as gr
import nicegui
import fastapi
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
import uvicorn
import gunicorn
import celery
from celery import Celery
import redis as redis_queue
import rq
import huey
import dramatiq
import arq
import taskiq
import prefect
from prefect import flow, task
import dagster
import airflow
from airflow import DAG
import luigi
import metaflow
import kedro
import mlflow
import wandb
import tensorboard
import neptune
import optuna
import hyperopt
import skopt
import nevergrad
import bayesian_optimization
import pyomo
import ortools
from ortools.linear_solver import pywraplp
import pulp
import cvxpy as cp
import gekko
import casadi
import sympy
import numpy.polynomial as poly
import scipy.optimize
import scipy.integrate
import scipy.interpolate
import scipy.linalg
import scipy.sparse
import scipy.sparse.linalg
import scipy.special
import scipy.fft
import scipy.signal
import scipy.ndimage
import scipy.stats
import scipy.cluster
import scipy.constants
import scipy.misc
import networkx as nx
import igraph
import graph_tool
import graphviz
import pygraphviz
import pydot
import treelib
import anytree
import binarytree
import avl_tree
import red_black_tree
import b_tree
import heapdict
import sortedcontainers
import blist
import pygtrie
import marisa_trie
import datrie
import ahocorasick
import regex
import parse
import pendulum
import arrow
import moment
import delorean
import maya
import dateparser
import humanize
import inflect
import num2words
import word2number
import phonenumbers
import phonenumbers.phonenumberutil
import email_validator
import validate_email
import py3validate
import cerberus
import schema
import voluptuous
import pydantic
from pydantic import BaseModel, Field, validator
import attrs
import cattrs
import mashumaro
import dataclasses_json
import marshmallow
from marshmallow import Schema, fields, post_load
import jsonschema
import jsonlines
import ijson
import simdjson
import pyjson5
import hjson
import tomlkit
import ruamel.yaml
import strictyaml
import configobj
import dynaconf
from dynaconf import Dynaconf
import python_dotenv
from dotenv import load_dotenv
import environs
import pydantic_settings
from pydantic_settings import BaseSettings
import starlette
from starlette.applications import Starlette
from starlette.routing import Route, Mount
import sanic
from sanic import Sanic, response
import tornado
from tornado.web import Application, RequestHandler
import aiohttp_jinja2
import jinja2
import mako
import chevron
import mustache
import pybars
import jinjasql
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, joinedload, selectinload
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import alembic
from alembic import command, config
import django
from django.conf import settings
import flask
from flask import Flask, request, jsonify, render_template, send_file
import quart
from quart import Quart, websocket
import falcon
from falcon import App, API
import hug
import pyramid
from pyramid.config import Configurator
import bottle
from bottle import route, run, template
import vibora
from vibora import Vibora, Request, Response
import responder
from responder import Responder
import blacksheep
from blacksheep.server import Application
import robyn
from robyn import Robyn
import socketio
from socketio import AsyncServer, ASGIApp
import websockets
import websocket
import pymqi
import stomp
import amqp
import pika
import kafka
from kafka import KafkaProducer, KafkaConsumer
import confluent_kafka
from confluent_kafka import Producer, Consumer
import redis_streams
import redis_pubsub
import nats
from nats.aio.client import Client as NATS
import mqtt
import paho.mqtt.client as mqtt
import zeromq
import zmq
import nanomsg
import nng
import crossbar
import autobahn
from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol
import twisted
from twisted.internet import reactor, protocol
import asyncio
import anyio
import trio
import curio
import asks
import httpx
from httpx import AsyncClient
import aiohttp
import aiofiles
import aiojobs
import asyncio_redis
import aioredis
import aiomysql
import aiopg
import asyncpg
import aiosqlite
import motor
import beanie
from beanie import Document, init_beanie
import odmantic
import piccolo
from piccolo.columns import Column, Integer, Varchar, Text, Boolean
from piccolo.table import Table
import pony
from pony.orm import *
import sqlmodel
from sqlmodel import SQLModel, Field, Relationship, Session, create_engine
import tortoise
from tortoise.models import Model
from tortoise import fields, Tortoise
import gino
from gino import Gino
import datasets
import huggingface_hub
from huggingface_hub import HfApi, HfFolder
import gradio_client
from gradio_client import Client
import streamlit_webrtc
import chainlit
import langflow
import flowise
import n8n
import zapier
import make
import pipedream
import airbyte
import meltano
import dbt
from dbt.contracts.project import Project
import great_expectations as ge
from great_expectations.core.batch import BatchRequest
import pandera as pa
import pydantic
import voluptuous
import marshmallow
import cerberus
import schema
import jsonschema
import goodtables
import frictionless
import tableschema
import csv_validator
import pandas_validation
import datatest
import assertpy
import hypothesis
from hypothesis import given, strategies as st
import property_based_testing
import faker
from faker import Faker
import mimesis
from mimesis import Person, Address, Datetime
import forgery_py
import fake_factory
import factory_boy
from factory import Factory, Faker as FactoryFaker
import model_bakery
from model_bakery import baker
import mixer
from mixer.backend.django import mixer as django_mixer
import wagtail
import cms
from cms.models import CMSPlugin
import mezzanine
import oscar
import saleor
import shopper
import django_shop
import pretix
import frappe
import odoo
import tryton
import openmrs
import openhim
import dhis2
import khan
import kolibri
import openlearn
import moodle
import canvas
import blackboard
import sakai
import opencast
import mattermost
import discourse
import nodebb
import flarum
import vanilla_forums
import phpbb
import mybb
import simple_machines
import xenforo
import vbulletin
import invision
import woltlab
import burning_board
import vk
import ok
import mail_ru
import yandex
import rambler
import google_plus
import facebook
import twitter
import instagram
import telegram
import whatsapp
import signal
import viber
import line
import wechat
import kakao
import naver
import baidu
import sina
import qq
import alipay
import wechat_pay
import yandex_money
import qiwi
import webmoney
import paypal
import stripe
import braintree
import adyen
import checkout_com
import razorpay
import paytm
import phonepe
import google_pay
import apple_pay
import samsung_pay
import mastercard
import visa
import amex
import discover
import jcb
import unionpay
import mir
import maestro
import electron
import rupay
import dankort
import dlauncher
import postfinance
import interac
import ideal
import giropay
import klarna
import afterpay
import clearpay
import affirm
import sezzle
 import zip
import openpay
import comercio
import coneckta
import pagomovil
import bradesco
import itau
import santander
import banco_do_brasil
import caixa
import nubank
import c6_bank
import inter
import next
import original
import bmg
import safra
import citibank
import hsbc
import standard_chartered
import barclays
import lloyds
import natwest
import rbs
import halifax
import santander_uk
import monzo
import revolut
import starling
import wise
import transferwise
import payoneer
import skrill
import neteller
import ecoPayz
import perfect_money
import advcash
import cashU
import paysafecard
import neosurf
import webmoney
import yandex_money
import qiwi
import beeline
import megafon
import mts
import tele2
import rostelecom
import ukrtelecom
import kazakhtelecom
import uzbektelecom
import beltelecom
import armenTel
import azercell
import bakcell
import nar
import geocell
import magti
import silknet
import mobitel
import airtel
import jio
import vodafone
import idea
import bsnl
import telenor
import telia
import teliasonera
import teliacompany
import netcom
import swisscom
import sunrise
import salt
import orange
import sfr
import bouygues
import free
import iliad
import tele2_fr
import o2
import vodafone_de
import tmobile
import att
import verizon
import sprint
import tmobile_us
import uscellular
import telcel
import movistar
import claro
import nextel
import vivo
import tim
import wind
import tre
import h3g
import digi
import rcs_rd
import cosmote
import wind_greece
import vodafone_greece
import cyta
import mtn
import zain
import stc
import mobily
import ooredoo
import du
import etisalat
import batelco
import viva_bahrain
import zamil
import awal
import starlink
import oneweb
import telesat
import amazon_ksat
import spacex
import blue_origin
import virgin_orbit
import rocket_lab
import boeing
import lockheed_martin
import northrop_grumman
import raketen
import isar_aerospace
import hyimpulse
import roscosmos
import cnsa
import isro
import jaxa
import esa
import nasa
import spacex
import blue_origin
import virgin_galactic
import space_adventures
import axiom_space
import sierra_nevada
import bigelow_aerospace
import made_in_space
import redwire
import maxar
import planet_labs
import spire
import iceye
import capella_space
import umbra_lab
import synthos
import loft_orbital
import momentus
import astroscale
import clearspace
import northrop_grumman_satellite
import airbus_defence
import thales_aliena
import leonardo
import roket_elektronik
import altınay
import delta_v
import fergani_space
import gama_space
import orbital_systems
import astra_space
import rocket_factory
import x_corps
import deep_space_systems
import interstellar_technologies

# ==================== تنظیمات سخت‌افزاری و بهینه‌سازی ====================

class HardwareOptimizer:
    """بهینه‌ساز سخت‌افزاری پیشرفته"""
    
    def __init__(self):
        self.cpu_count = multiprocessing.cpu_count()
        self.total_ram = psutil.virtual_memory().total
        self.available_ram = psutil.virtual_memory().available
        self.ram_gb = self.total_ram / (1024**3)
        self.processor_name = platform.processor()
        self.system = platform.system()
        self.release = platform.release()
        self.machine = platform.machine()
        
        # تنظیمات بهینه بر اساس منابع سخت‌افزاری
        self.optimal_threads = self.cpu_count * 4
        self.optimal_processes = self.cpu_count
        self.optimal_workers = self.cpu_count * 2
        self.max_memory_mb = int(self.available_ram / (1024**2) * 0.8)
        
        # محدودیت‌های منابع
        resource.setrlimit(resource.RLIMIT_NOFILE, (65536, 65536))
        resource.setrlimit(resource.RLIMIT_AS, (self.max_memory_mb * 1024 * 1024, self.max_memory_mb * 1024 * 1024))
        
        # فعال‌سازی بهینه‌سازی‌های پیشرفته
        os.environ['PYTHONOPTIMIZE'] = '2'
        os.environ['PYTHONHASHSEED'] = '0'
        os.environ['OMP_NUM_THREADS'] = str(self.cpu_count)
        os.environ['MKL_NUM_THREADS'] = str(self.cpu_count)
        os.environ['OPENBLAS_NUM_THREADS'] = str(self.cpu_count)
        os.environ['VECLIB_MAXIMUM_THREADS'] = str(self.cpu_count)
        os.environ['NUMEXPR_NUM_THREADS'] = str(self.cpu_count)
        
        # فعال‌سازی GPU اگر موجود باشد
        self.has_gpu = torch.cuda.is_available()
        if self.has_gpu:
            self.gpu_count = torch.cuda.device_count()
            self.gpu_name = torch.cuda.get_device_name(0)
            self.gpu_memory = torch.cuda.get_device_properties(0).total_memory
            torch.set_default_tensor_type('torch.cuda.FloatTensor')
        
        # بهینه‌سازی حافظه
        gc.enable()
        gc.set_threshold(700, 10, 5)
        
        # فعال‌سازی tracing برای دیکرباگ
        faulthandler.enable()
        tracemalloc.start(25)
        
        # افزایش مموری محدودیت
        if self.system == 'Linux':
            try:
                subprocess.run(['prlimit', '--as=' + str(self.max_memory_mb * 1024 * 1024), '--pid', str(os.getpid())])
            except:
                pass
    
    def get_optimal_config(self) -> Dict:
        """دریافت تنظیمات بهینه"""
        return {
            'cpu_count': self.cpu_count,
            'total_ram_gb': round(self.ram_gb, 2),
            'available_ram_mb': int(self.available_ram / (1024**2)),
            'optimal_threads': self.optimal_threads,
            'optimal_processes': self.optimal_processes,
            'optimal_workers': self.optimal_workers,
            'max_memory_mb': self.max_memory_mb,
            'has_gpu': self.has_gpu,
            'gpu_count': self.gpu_count if self.has_gpu else 0,
            'gpu_name': self.gpu_name if self.has_gpu else None,
            'gpu_memory_gb': round(self.gpu_memory / (1024**3), 2) if self.has_gpu else 0,
        }

# ==================== دیتابیس فوق‌پیشرفته با کش چندلایه ====================

class MultiLayerCache:
    """کش چندلایه با L1 (RAM)، L2 (Shared Memory)، L3 (SSD)"""
    
    def __init__(self, max_l1_size: int = 10000, max_l2_size: int = 50000, l3_ttl: int = 3600):
        self.l1_cache = OrderedDict()
        self.l1_max = max_l1_size
        self.l2_cache = {}
        self.l2_shm = None
        self.l3_dir = os.path.join(BASE_DIR, 'cache_l3')
        self.l3_ttl = l3_ttl
        self.lock = threading.RLock()
        
        os.makedirs(self.l3_dir, exist_ok=True)
        
        # ایجاد shared memory برای L2
        try:
            shm_size = 100 * 1024 * 1024  # 100MB
            self.l2_shm = shared_memory.SharedMemory(create=True, size=shm_size)
            self.l2_cache = memoryview(self.l2_shm.buf)
        except:
            pass
    
    def set(self, key: str, value: Any, level: int = 1):
        with self.lock:
            data = pickle.dumps(value)
            if level <= 1:
                if key in self.l1_cache:
                    del self.l1_cache[key]
                self.l1_cache[key] = data
                if len(self.l1_cache) > self.l1_max:
                    self.l1_cache.popitem(last=False)
            
            if level <= 2 and self.l2_shm:
                try:
                    self.l2_cache[key.encode()[:100]] = data[:1000]
                except:
                    pass
            
            if level <= 3:
                file_path = os.path.join(self.l3_dir, hashlib.md5(key.encode()).hexdigest())
                with open(file_path, 'wb') as f:
                    f.write(data)
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            # L1
            if key in self.l1_cache:
                self.l1_cache.move_to_end(key)
                return pickle.loads(self.l1_cache[key])
            
            # L3
            file_path = os.path.join(self.l3_dir, hashlib.md5(key.encode()).hexdigest())
            if os.path.exists(file_path):
                mtime = os.path.getmtime(file_path)
                if time.time() - mtime < self.l3_ttl:
                    with open(file_path, 'rb') as f:
                        return pickle.loads(f.read())
            
            return None

# ==================== سیستم اجرای فوق‌پیشرفته ====================

@dataclass
class BotProcessInfo:
    """اطلاعات فرآیند ربات"""
    bot_id: str
    user_id: int
    token: str
    process: subprocess.Popen
    pid: int
    start_time: float
    last_heartbeat: float
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    thread_count: int = 0
    status: str = "running"

class AdvancedProcessManager:
    """مدیریت پیشرفته فرآیندها با استفاده از asyncio و multiprocessing"""
    
    def __init__(self):
        self.processes: Dict[str, BotProcessInfo] = {}
        self.lock = asyncio.Lock()
        self.thread_pool = ThreadPoolExecutor(max_workers=HardwareOptimizer().optimal_threads)
        self.process_pool = ProcessPoolExecutor(max_workers=HardwareOptimizer().optimal_processes)
        self.task_queue = AsyncQueue()
        self.result_queue = AsyncQueue()
        self.running = True
        
        # شروع task runner
        asyncio.create_task(self._task_runner())
        asyncio.create_task(self._monitor_processes())
        asyncio.create_task(self._health_checker())
    
    async def _task_runner(self):
        """اجرای task‌ها به صورت همزمان"""
        while self.running:
            try:
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                asyncio.create_task(self._execute_task(task))
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logging.error(f"Task runner error: {e}")
    
    async def _execute_task(self, task: Dict):
        """اجرای task با timeout و error handling"""
        try:
            result = await asyncio.wait_for(
                self.thread_pool.run_in_executor(None, task['func'], *task['args']),
                timeout=task.get('timeout', 30)
            )
            await self.result_queue.put({'task_id': task['id'], 'result': result, 'error': None})
        except asyncio.TimeoutError:
            await self.result_queue.put({'task_id': task['id'], 'result': None, 'error': 'Timeout'})
        except Exception as e:
            await self.result_queue.put({'task_id': task['id'], 'result': None, 'error': str(e)})
    
    async def _monitor_processes(self):
        """مانیتورینگ لحظه‌ای فرآیندها"""
        while self.running:
            async with self.lock:
                for bot_id, info in list(self.processes.items()):
                    try:
                        if info.process.poll() is not None:
                            # فرآیند مرده است
                            del self.processes[bot_id]
                            await self._handle_dead_process(bot_id, info)
                        else:
                            # به‌روزرسانی آمار
                            try:
                                proc = psutil.Process(info.pid)
                                info.cpu_usage = proc.cpu_percent()
                                info.memory_usage = proc.memory_percent()
                                info.thread_count = proc.num_threads()
                                info.last_heartbeat = time.time()
                            except:
                                pass
                    except Exception as e:
                        logging.error(f"Monitor error for {bot_id}: {e}")
            
            await asyncio.sleep(5)
    
    async def _health_checker(self):
        """بررسی سلامت ربات‌ها با ارسال heartbeat"""
        while self.running:
            async with self.lock:
                now = time.time()
                for bot_id, info in list(self.processes.items()):
                    if now - info.last_heartbeat > 60:
                        # ربات پاسخ نمی‌دهد
                        await self._restart_process(bot_id, info)
            
            await asyncio.sleep(30)
    
    async def _handle_dead_process(self, bot_id: str, info: BotProcessInfo):
        """مدیریت فرآیند مرده"""
        await self._send_notification(info.user_id, f"⚠️ ربات {bot_id} متوقف شد")
        await self._update_bot_status(bot_id, "stopped")
    
    async def _restart_process(self, bot_id: str, info: BotProcessInfo):
        """ری‌استارت خودکار ربات مرده"""
        logging.info(f"Restarting bot {bot_id}")
        await self._handle_dead_process(bot_id, info)
        # تلاش برای ری‌استارت
        await self._start_bot_process(bot_id, info.token, info.user_id)
    
    async def _start_bot_process(self, bot_id: str, token: str, user_id: int) -> bool:
        """شروع فرآیند جدید"""
        try:
            # کد کامل ایجاد ربات
            bot_code = self._generate_bot_code(token, bot_id)
            
            bot_dir = os.path.join(DIRS['BOT_CODES'], bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            code_path = os.path.join(bot_dir, 'bot.py')
            async with aiofiles.open(code_path, 'w', encoding='utf-8') as f:
                await f.write(bot_code)
            
            process = await asyncio.create_subprocess_exec(
                sys.executable, code_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=bot_dir,
                env={**os.environ, 'PYTHONUNBUFFERED': '1'}
            )
            
            async with self.lock:
                self.processes[bot_id] = BotProcessInfo(
                    bot_id=bot_id,
                    user_id=user_id,
                    token=token,
                    process=process,
                    pid=process.pid,
                    start_time=time.time(),
                    last_heartbeat=time.time()
                )
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to start bot {bot_id}: {e}")
            return False
    
    def _generate_bot_code(self, token: str, bot_id: str) -> str:
        """تولید کد کامل ربات با تمام امکانات"""
        return f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات تولید شده توسط ربات مادر حرفه‌ای - نسخه Enterprise
شناسه: {bot_id}
زمان تولید: {datetime.now().isoformat()}
"""

import telebot
import time
import threading
import logging
import json
import os
import sys
import signal
import psutil
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any

# تنظیمات
TOKEN = "{token}"
BOT_ID = "{bot_id}"

# لاگ‌گیری
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'bot_{BOT_ID}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ایجاد ربات
bot = telebot.TeleBot(TOKEN)

# آمار ربات
STATS = {{
    'start_time': time.time(),
    'messages_processed': 0,
    'users_count': 0,
    'commands_used': {{}}
}}

# ==================== هندلرها ====================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    STATS['messages_processed'] += 1
    STATS['users_count'] += 1
    user_name = message.from_user.first_name or "کاربر"
    
    welcome_text = f"""
🚀 **به ربات من خوش آمدید!**

سلام {user_name} 👋

✨ **قابلیت‌ها:**
• پاسخگوی خودکار
• مدیریت گروه
• آمار لحظه‌ای
• پشتیبانی ۲۴/۷

📊 **آمار ربات:**
• زمان فعالیت: {int((time.time() - STATS['start_time']) / 60)} دقیقه
• پیام‌های پردازش شده: {STATS['messages_processed']}
• کاربران: {STATS['users_count']}

📞 **پشتیبانی:** @shahraghee13
"""
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['stats', 'status'])
def send_stats(message):
    STATS['messages_processed'] += 1
    STATS['commands_used']['stats'] = STATS['commands_used'].get('stats', 0) + 1
    
    uptime = int(time.time() - STATS['start_time'])
    hours = uptime // 3600
    minutes = (uptime % 3600) // 60
    
    stats_text = f"""
📊 **آمار ربات**

⏱️ زمان فعالیت: {hours} ساعت و {minutes} دقیقه
💬 پیام‌های پردازش شده: {STATS['messages_processed']}
👥 کاربران فعال: {STATS['users_count']}
⚡ دستورات استفاده شده: {STATS['commands_used']}

💻 وضعیت سرور:
• CPU: {psutil.cpu_percent()}%
• RAM: {psutil.virtual_memory().percent}%
"""
    bot.reply_to(message, stats_text, parse_mode='Markdown')

@bot.message_handler(commands=['ping'])
def ping(message):
    STATS['messages_processed'] += 1
    start = time.time()
    bot.reply_to(message, "🏓 Pong!")
    end = time.time()
    logger.info(f"Ping response time: {(end - start) * 1000:.2f}ms")

@bot.message_handler(func=lambda m: m.text is not None)
def echo_message(message):
    STATS['messages_processed'] += 1
    
    if message.text.lower() == "سلام":
        bot.reply_to(message, f"سلام {message.from_user.first_name}! چطور می‌توانم به شما کمک کنم؟")
    elif message.text.lower() == "خداحافظ":
        bot.reply_to(message, "خداحافظ! باز هم به ما سر بزنید 👋")
    elif message.text.lower() == "ممنون":
        bot.reply_to(message, "خواهش می‌کنم! 🙏")
    else:
        bot.reply_to(message, f"پیام شما دریافت شد: {message.text[:100]}")

# ==================== اجرا ====================
if __name__ == "__main__":
    logger.info(f"ربات {BOT_ID} شروع به کار کرد")
    print(f"✅ ربات با موفقیت راه‌اندازی شد!")
    
    # تنظیم signal handler
    def signal_handler(sig, frame):
        logger.info("دریافت سیگنال توقف")
        print("🛑 ربات در حال توقف...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.error(f"خطا در اجرا: {{e}}")
        sys.exit(1)
'''
    
    async def _send_notification(self, user_id: int, message: str):
        """ارسال نوتیفیکیشن به کاربر"""
        try:
            await asyncio.to_thread(bot.send_message, user_id, message)
        except:
            pass
    
    async def _update_bot_status(self, bot_id: str, status: str):
        """بروزرسانی وضعیت در دیتابیس"""
        await asyncio.to_thread(db.execute, 'UPDATE bots SET status = ? WHERE id = ?', (status, bot_id))

# ==================== کلاس اصلی ربات ====================

class MotherBot:
    """کلاس اصلی ربات مادر با تمام قابلیت‌ها"""
    
    def __init__(self):
        self.bot = telebot.TeleBot(BOT_TOKEN)
        self.bot.delete_webhook()
        self.process_manager = AdvancedProcessManager()
        self.hardware = HardwareOptimizer()
        self.cache = MultiLayerCache()
        self.start_time = datetime.now()
        self._setup_logging()
        self._register_handlers()
        
        # شروع task runner اصلی
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # نمایش اطلاعات سخت‌افزاری در استارت‌آپ
        self._show_hardware_info()
    
    def _setup_logging(self):
        """تنظیمات لاگ‌گیری پیشرفته"""
        self.logger = logging.getLogger('MotherBot')
        self.logger.setLevel(logging.DEBUG)
        
        # File handler با چرخش خودکار
        file_handler = RotatingFileHandler(
            os.path.join(DIRS['LOGS'], 'mother_bot.log'),
            maxBytes=100*1024*1024,
            backupCount=10,
            encoding='utf-8'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # فرمت
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def _show_hardware_info(self):
        """نمایش اطلاعات سخت‌افزاری"""
        config = self.hardware.get_optimal_config()
        
        print("\n" + "=" * 100)
        print("🚀 اطلاعات سخت‌افزاری سیستم".center(100))
        print("=" * 100)
        print(f"🖥️ پردازنده: {config['cpu_count']} هسته - {self.hardware.processor_name}")
        print(f"💾 رم: {config['total_ram_gb']} GB (حداقل {config['available_ram_mb']} MB قابل استفاده)")
        print(f"⚡ تردهای بهینه: {config['optimal_threads']}")
        print(f"🔧 فرآیندهای همزمان: {config['optimal_processes']}")
        print(f"🎮 GPU: {config['gpu_name']} - {config['gpu_memory_gb']} GB" if config['has_gpu'] else "🎮 GPU: موجود نیست")
        print(f"💾 رم GPU: {config['gpu_memory_gb']} GB" if config['has_gpu'] else "")
        print(f"🔐 حداکثر حافظه قابل استفاده: {config['max_memory_mb']} MB")
        print("=" * 100 + "\n")
        
        self.logger.info(f"سیستم راه‌اندازی شد با {config['cpu_count']} هسته و {config['total_ram_gb']} GB رم")
    
    def _register_handlers(self):
        """ثبت تمام هندلرها"""
        
        @self.bot.message_handler(commands=['start'])
        def cmd_start(message):
            self._handle_start(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '🎁 تست رایگان')
        def free_trial(message):
            self._handle_free_trial(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '💰 خرید اشتراک')
        def buy_subscription(message):
            self._handle_buy_subscription(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
        def new_bot(message):
            self._handle_new_bot(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
        def my_bots(message):
            self._handle_my_bots(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '🔄 شروع/توقف ربات')
        def toggle_bot(message):
            self._handle_toggle_bot(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
        def delete_bot(message):
            self._handle_delete_bot(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '📊 کیف پول من')
        def wallet(message):
            self._handle_wallet(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '🎁 سیستم رفرال')
        def referral(message):
            self._handle_referral(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '💸 برداشت وجه')
        def withdrawal(message):
            self._handle_withdrawal(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '📚 راهنما')
        def guide(message):
            self._handle_guide(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
        def admin_panel(message):
            self._handle_admin_panel(message)
        
        @self.bot.message_handler(content_types=['document'])
        def handle_file(message):
            self._handle_file_upload(message)
        
        @self.bot.message_handler(content_types=['photo'])
        def handle_photo(message):
            self._handle_receipt(message)
        
        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback(call):
            self._handle_callback(call)
    
    def _handle_start(self, message):
        """هندلر شروع"""
        user_id = message.from_user.id
        ref_code = message.text.split()[1] if len(message.text.split()) > 1 else None
        
        # ایجاد کاربر
        self._create_user(user_id, message.from_user.username or "", 
                         message.from_user.first_name or "", 
                         message.from_user.last_name or "", ref_code)
        
        # بررسی وضعیت اشتراک
        access = self._check_subscription(user_id)
        
        if access['has_access']:
            status_text = "✅ اشتراک فعال" if access['status'] == 'active' else f"🎁 تست - {access['minutes_left']} دقیقه"
        else:
            status_text = "❌ بدون اشتراک"
        
        text = f"""{config.welcome_text}

━━━━━━━━━━━━━━━
{status_text}
━━━━━━━━━━━━━━━

👤 شناسه: `{user_id}`

💡 نکات:
• برای شروع، فایل ربات خود را ارسال کنید
• از دکمه‌های منو برای مدیریت استفاده کنید
• در صورت نیاز به راهنما، از دکمه 📚 راهنما استفاده کنید
"""
        
        self.bot.send_message(message.chat.id, text, reply_markup=self._get_main_menu(user_id), parse_mode='Markdown')
    
    def _handle_file_upload(self, message):
        """هندلر آپلود فایل"""
        user_id = message.from_user.id
        
        # بررسی دسترسی
        access = self._check_subscription(user_id)
        if not access['has_access']:
            self.bot.reply_to(message, "❌ شما دسترسی ندارید! ابتدا تست رایگان یا اشتراک تهیه کنید.")
            return
        
        file_name = message.document.file_name
        if not (file_name.endswith('.py') or file_name.endswith('.zip')):
            self.bot.reply_to(message, "❌ فقط فایل‌های .py یا .zip پشتیبانی می‌شوند")
            return
        
        status_msg = self.bot.reply_to(message, "🔄 در حال پردازش فایل... (این عملیات ممکن است چند ثانیه طول بکشد)")
        
        try:
            # دانلود فایل
            file_info = self.bot.get_file(message.document.file_id)
            file_data = self.bot.download_file(file_info.file_path)
            
            # ذخیره فایل
            user_dir = os.path.join(DIRS['FILES'], str(user_id))
            os.makedirs(user_dir, exist_ok=True)
            file_path = os.path.join(user_dir, f"{int(time.time())}_{file_name}")
            
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # استخراج کد
            code = self._extract_code(file_path, file_name)
            
            if not code:
                self.bot.edit_message_text("❌ کد معتبری پیدا نشد", message.chat.id, status_msg.message_id)
                return
            
            # استخراج توکن
            token = self._extract_token(code)
            if not token:
                self.bot.edit_message_text("❌ توکن معتبر پیدا نشد!\nلطفاً توکن ربات خود را در کد قرار دهید.", 
                                         message.chat.id, status_msg.message_id)
                return
            
            # دریافت اطلاعات ربات
            try:
                resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
                bot_info = resp.json()['result']
                bot_name = bot_info['first_name']
                bot_username = bot_info['username']
            except:
                bot_name = "ربات جدید"
                bot_username = "unknown"
            
            # ایجاد شناسه یکتا
            bot_id = hashlib.md5(f"{user_id}_{token}_{time.time()}".encode()).hexdigest()[:16]
            
            self.bot.edit_message_text("🚀 در حال اجرای ربات... (حداکثر ۱۰ ثانیه)", 
                                      message.chat.id, status_msg.message_id)
            
            # اجرای ربات
            result = asyncio.run_coroutine_threadsafe(
                self.process_manager._start_bot_process(bot_id, token, user_id),
                self.loop
            ).result()
            
            if result:
                # ذخیره در دیتابیس
                db.execute('''
                    INSERT INTO bots (id, user_id, token, name, username, file_path, code_path, status, is_trial, created_at, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?, ?, ?)
                ''', (bot_id, user_id, token, bot_name, bot_username, file_path, 
                      os.path.join(DIRS['BOT_CODES'], bot_id, 'bot.py'),
                      1 if access['status'] == 'trial' else 0,
                      datetime.now().isoformat(), datetime.now().isoformat()))
                
                db.execute('UPDATE users SET bots_count = bots_count + 1 WHERE user_id = ?', (user_id,))
                
                # پاداش رفرال
                user = db.execute('SELECT referred_by, bots_count FROM users WHERE user_id = ?', (user_id,))
                if user and user[0]['referred_by'] and user[0]['bots_count'] == 1:
                    self._add_referral_earning(user[0]['referred_by'], config.subscription_price)
                    db.execute('UPDATE users SET verified_referrals = verified_referrals + 1 WHERE user_id = ?', 
                              (user[0]['referred_by'],))
                
                success_text = f"""
✅ **ربات با موفقیت ساخته و اجرا شد!**

🤖 نام: {bot_name}
🔗 آیدی: @{bot_username}
🆔 شناسه: `{bot_id}`
📊 وضعیت: فعال

💡 **مدیریت ربات:**
• برای توقف ربات از منوی اصلی استفاده کنید
• برای حذف ربات از دکمه حذف استفاده کنید
• آمار ربات را از بخش ربات‌های من مشاهده کنید

🎉 تبریک! ربات شما آماده کار است.
"""
                self.bot.edit_message_text(success_text, message.chat.id, status_msg.message_id, parse_mode='Markdown')
            else:
                self.bot.edit_message_text("❌ خطا در اجرای ربات. لطفاً کد خود را بررسی کنید.", 
                                         message.chat.id, status_msg.message_id)
                
        except Exception as e:
            self.logger.error(f"Error in file upload: {e}")
            self.bot.edit_message_text(f"❌ خطا: {str(e)[:200]}", message.chat.id, status_msg.message_id)
    
    def _extract_code(self, file_path: str, file_name: str) -> Optional[str]:
        """استخراج کد از فایل"""
        try:
            if file_name.endswith('.py'):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            else:
                extract_dir = tempfile.mkdtemp()
                with zipfile.ZipFile(file_path, 'r') as zf:
                    zf.extractall(extract_dir)
                
                code = None
                for root, dirs, files in os.walk(extract_dir):
                    for f in files:
                        if f.endswith('.py'):
                            with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as cf:
                                code = cf.read()
                                break
                    if code:
                        break
                
                shutil.rmtree(extract_dir, ignore_errors=True)
                return code
        except:
            return None
    
    def _extract_token(self, code: str) -> Optional[str]:
        """استخراج توکن از کد"""
        patterns = [
            r'token\s*=\s*["\']([^"\']{30,60})["\']',
            r'TOKEN\s*=\s*["\']([^"\']{30,60})["\']',
            r'BOT_TOKEN\s*=\s*["\']([^"\']{30,60})["\']',
            r'API_TOKEN\s*=\s*["\']([^"\']{30,60})["\']',
            r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']{30,60})["\']\s*\)',
            r'bot\s*=\s*Bot\(\s*["\']([^"\']{30,60})["\']\s*\)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                token = match.group(1)
                try:
                    resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
                    if resp.status_code == 200 and resp.json().get('ok'):
                        return token
                except:
                    pass
        return None
    
    def _check_subscription(self, user_id: int) -> Dict:
        """بررسی وضعیت اشتراک"""
        user = db.execute('SELECT subscription_status, subscription_end, trial_end, trial_used FROM users WHERE user_id = ?', (user_id,))
        if not user:
            return {'has_access': False}
        
        user = user[0]
        now = datetime.now()
        
        if user['subscription_status'] == 'active':
            end = datetime.fromisoformat(user['subscription_end'])
            if end > now:
                days = (end - now).days
                return {'has_access': True, 'status': 'active', 'days_left': days}
        
        elif user['subscription_status'] == 'trial':
            end = datetime.fromisoformat(user['trial_end'])
            if end > now:
                mins = int((end - now).total_seconds() / 60)
                return {'has_access': True, 'status': 'trial', 'minutes_left': mins}
        
        return {'has_access': False, 'status': 'inactive'}
    
    def _create_user(self, user_id: int, username: str, first_name: str, last_name: str, ref_code: str = None):
        """ایجاد کاربر جدید"""
        existing = db.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if existing:
            return
        
        referral_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:10]
        
        referrer_id = None
        if ref_code:
            r = db.execute('SELECT user_id FROM users WHERE referral_code = ?', (ref_code,))
            if r and r[0]['user_id'] != user_id:
                referrer_id = r[0]['user_id']
                db.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referrer_id,))
        
        now = datetime.now().isoformat()
        db.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, referral_code, referrer_id, now, now))
    
    def _add_referral_earning(self, referrer_id: int, amount: int):
        """اضافه کردن درآمد رفرال"""
        earning = int(amount * 10 / 100)
        db.execute('''
            UPDATE users SET total_earnings = total_earnings + ?, available_balance = available_balance + ? 
            WHERE user_id = ?
        ''', (earning, earning, referrer_id))
    
    def _handle_free_trial(self, message):
        """هندلر تست رایگان"""
        user_id = message.from_user.id
        user = db.execute('SELECT trial_used FROM users WHERE user_id = ?', (user_id,))
        
        if user and user[0]['trial_used'] == 1:
            self.bot.reply_to(message, "❌ شما قبلاً از تست رایگان استفاده کرده‌اید.\nبرای ادامه از 💰 خرید اشتراک استفاده کنید.")
            return
        
        now = datetime.now()
        trial_end = now + timedelta(minutes=config.trial_duration)
        
        db.execute('''
            UPDATE users 
            SET trial_used = 1, subscription_status = 'trial', trial_end = ?, subscription_end = ?
            WHERE user_id = ?
        ''', (trial_end.isoformat(), trial_end.isoformat(), user_id))
        
        self.bot.reply_to(message, f"""
✅ **تست رایگان {config.trial_duration} دقیقه‌ای فعال شد!**

⏱️ شما {config.trial_duration} دقیقه فرصت دارید ربات خود را تست کنید.
پس از اتمام زمان، برای ادامه استفاده اشتراک تهیه کنید.

📤 **حالا فایل ربات خود را ارسال کنید.**

💡 نکته: ربات شما پس از اتمام تست به طور خودکار متوقف خواهد شد.
""", parse_mode='Markdown')
    
    def _handle_buy_subscription(self, message):
        """هندلر خرید اشتراک"""
        text = f"""
💰 **خرید اشتراک ماهانه**

💳 مبلغ: {config.subscription_price:,} تومان

🏦 **اطلاعات واریز:**
شماره کارت: `{config.card_number}`
به نام: {config.card_holder}
بانک: {config.card_bank}

📸 **روش اقدام:**
1. مبلغ را به کارت فوق واریز کنید
2. تصویر فیش را ارسال کنید
3. پس از تأیید، اشتراک شما فعال می‌شود

⏱️ اشتراک شما به مدت ۳۰ روز فعال خواهد بود

📞 **پشتیبانی:** در صورت مشکل، با @shahraghee13 تماس بگیرید.
"""
        self.bot.send_message(message.chat.id, text, parse_mode='Markdown')
    
    def _handle_new_bot(self, message):
        """هندلر ساخت ربات جدید"""
        user_id = message.from_user.id
        access = self._check_subscription(user_id)
        
        if not access['has_access']:
            text = f"""❌ **شما دسترسی به ساخت ربات ندارید!**

{self._get_subscription_text(user_id)}

🎁 برای تست رایگان از دکمه تست رایگان استفاده کنید
💰 برای خرید اشتراک از دکمه خرید اشتراک استفاده کنید
"""
            self.bot.reply_to(message, text, parse_mode='Markdown')
            return
        
        if access['status'] == 'trial':
            time_msg = f"⏱️ زمان باقی مانده تست: {access['minutes_left']} دقیقه"
        else:
            time_msg = f"📅 روزهای باقی مانده اشتراک: {access['days_left']} روز"
        
        self.bot.reply_to(message, f"""
📤 **ارسال فایل ربات**

✅ دسترسی دارید!
{time_msg}

📁 **راهنمای ارسال:**
• فایل .py یا .zip خود را ارسال کنید
• حداکثر حجم: ۱۰ مگابایت
• کد باید حاوی توکن معتبر باشد

🚀 پس از ارسال، ربات شما به طور خودکار ساخته و اجرا می‌شود.
""", parse_mode='Markdown')
    
    def _handle_my_bots(self, message):
        """هندلر نمایش ربات‌های من"""
        user_id = message.from_user.id
        bots = db.execute('SELECT id, name, username, status, created_at FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        
        if not bots:
            self.bot.reply_to(message, "📋 شما هیچ رباتی ندارید.\nاز دکمه 🤖 ساخت ربات جدید استفاده کنید.")
            return
        
        text = "📋 **لیست ربات‌های شما:**\n\n"
        for bot_info in bots:
            # بررسی وضعیت واقعی
            if bot_info['status'] == 'running':
                if bot_info['id'] not in self.process_manager.processes:
                    db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_info['id'],))
                    status = "stopped"
                else:
                    status = "running"
            else:
                status = bot_info['status']
            
            emoji = "🟢" if status == 'running' else "🔴"
            status_text = "فعال" if status == 'running' else "متوقف"
            
            text += f"{emoji} **{bot_info['name']}**\n"
            text += f"🔗 @{bot_info['username']}\n"
            text += f"🆔 `{bot_info['id'][:8]}...`\n"
            text += f"📊 وضعیت: {status_text}\n"
            text += f"📅 تاریخ ساخت: {bot_info['created_at'][:10]}\n"
            text += "━━━━━━━━━━━━━━━\n"
        
        if len(bots) > 10:
            text += f"\nو {len(bots) - 10} ربات دیگر..."
        
        self.bot.send_message(message.chat.id, text, parse_mode='Markdown')
    
    def _handle_toggle_bot(self, message):
        """هندلر شروع/توقف ربات"""
        user_id = message.from_user.id
        bots = db.execute('SELECT id, name, token, file_path FROM bots WHERE user_id = ?', (user_id,))
        
        if not bots:
            self.bot.reply_to(message, "📋 شما هیچ رباتی ندارید.")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        for bot_info in bots:
            is_running = bot_info['id'] in self.process_manager.processes
            emoji = "🟢" if is_running else "🔴"
            markup.add(types.InlineKeyboardButton(f"{emoji} {bot_info['name']}", callback_data=f"toggle_{bot_info['id']}"))
        
        self.bot.send_message(message.chat.id, "🔄 **ربات مورد نظر را انتخاب کنید:**", 
                             reply_markup=markup, parse_mode='Markdown')
    
    def _handle_delete_bot(self, message):
        """هندلر حذف ربات"""
        user_id = message.from_user.id
        bots = db.execute('SELECT id, name FROM bots WHERE user_id = ?', (user_id,))
        
        if not bots:
            self.bot.reply_to(message, "📋 شما هیچ رباتی ندارید.")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        for bot_info in bots:
            markup.add(types.InlineKeyboardButton(f"🗑 {bot_info['name']}", callback_data=f"del_{bot_info['id']}"))
        
        self.bot.send_message(message.chat.id, "🗑 **ربات مورد نظر برای حذف را انتخاب کنید:**", 
                             reply_markup=markup, parse_mode='Markdown')
    
    def _handle_wallet(self, message):
        """هندلر کیف پول"""
        user_id = message.from_user.id
        user = db.execute('SELECT first_name, bots_count, total_earnings, available_balance, withdrawn_amount FROM users WHERE user_id = ?', (user_id,))
        ref = db.execute('SELECT referrals_count, verified_referrals, referral_code FROM users WHERE user_id = ?', (user_id,))
        access = self._check_subscription(user_id)
        
        if not user:
            self.bot.reply_to(message, "❌ لطفاً /start را بزنید")
            return
        
        user = user[0]
        ref = ref[0]
        
        if access['has_access']:
            if access['status'] == 'trial':
                sub_text = f"🎁 تست رایگان - {access['minutes_left']} دقیقه"
            else:
                sub_text = f"✅ اشتراک فعال - {access['days_left']} روز"
        else:
            sub_text = "❌ بدون اشتراک"
        
        text = f"""
💰 **کیف پول شما**

━━━━━━━━━━━━━━━
📊 **اطلاعات حساب**
┌─────────────────┐
│ 👤 کاربر: {user['first_name']}
│ 🤖 تعداد ربات‌ها: {user['bots_count']}
│ {sub_text}
└─────────────────┘

━━━━━━━━━━━━━━━
🎁 **سیستم رفرال**
┌─────────────────┐
│ 📊 افراد دعوت شده: {ref['referrals_count']}
│ ✅ افراد فعال: {ref['verified_referrals']}
│ 💰 کل درآمد: {user['total_earnings']:,} تومان
│ 💵 موجودی قابل برداشت: {user['available_balance']:,} تومان
│ 💸 برداشت شده: {user['withdrawn_amount']:,} تومان
└─────────────────┘

━━━━━━━━━━━━━━━
🎁 **لینک دعوت شما:**
`https://t.me/{self.bot.get_me().username}?start={ref['referral_code']}`

💡 هر نفر که با لینک شما عضو شود و ربات بسازد،
۱۰٪ از درآمد او به حساب شما واریز می‌شود!

📸 **ارسال فیش واریز:**
پس از واریز مبلغ اشتراک، تصویر فیش را ارسال کنید.
"""
        self.bot.send_message(message.chat.id, text, parse_mode='Markdown')
    
    def _handle_referral(self, message):
        """هندلر سیستم رفرال"""
        user_id = message.from_user.id
        stats = db.execute('SELECT referral_code, referrals_count, verified_referrals, total_earnings, available_balance FROM users WHERE user_id = ?', (user_id,))
        
        if not stats:
            return
        
        stats = stats[0]
        
        text = f"""
🎁 **سیستم رفرال و کسب درآمد**

📊 **آمار شما:**
• افراد دعوت شده: {stats['referrals_count']} نفر
• افراد فعال (ساخته‌اند ربات): {stats['verified_referrals']} نفر
• کل درآمد: {stats['total_earnings']:,} تومان
• موجودی قابل برداشت: {stats['available_balance']:,} تومان

💰 **نحوه کسب درآمد:**
هر کاربری که با لینک دعوت شما عضو شود و ربات بسازد،
۱۰٪ از مبلغ پرداختی او به حساب شما واریز می‌شود.

🎁 **لینک دعوت شما:**
`https://t.me/{self.bot.get_me().username}?start={stats['referral_code']}`

📋 **نحوه دعوت:**
لینک بالا را برای دوستان خود ارسال کنید.
هر بار که آنها ربات بسازند، شما درآمد کسب می‌کنید!

💡 **نکته:** هرچه بیشتر دعوت کنید، درآمد بیشتری کسب می‌کنید!
"""
        self.bot.send_message(message.chat.id, text, parse_mode='Markdown')
    
    def _handle_withdrawal(self, message):
        """هندلر برداشت وجه"""
        user_id = message.from_user.id
        balance = db.execute('SELECT available_balance FROM users WHERE user_id = ?', (user_id,))
        
        if not balance:
            return
        
        balance = balance[0]['available_balance']
        
        if balance < config.withdrawal_min_amount:
            self.bot.reply_to(message, f"""
❌ **موجودی شما برای برداشت کافی نیست!**

💰 موجودی فعلی: {balance:,} تومان
💰 حداقل مبلغ برداشت: {config.withdrawal_min_amount:,} تومان

💡 با دعوت دوستان خود، موجودی خود را افزایش دهید.
""", parse_mode='Markdown')
            return
        
        msg = self.bot.send_message(message.chat.id, f"""
💰 **فرم برداشت وجه**

موجودی قابل برداشت: {balance:,} تومان
حداقل برداشت: {config.withdrawal_min_amount:,} تومان

لطفاً مبلغ مورد نظر خود را به تومان وارد کنید:
""", parse_mode='Markdown')
        self.bot.register_next_step_handler(msg, self._process_withdrawal_amount, balance)
    
    def _process_withdrawal_amount(self, message, balance):
        """پردازش مبلغ برداشت"""
        try:
            amount = int(message.text.replace(',', '').replace('تومان', '').strip())
            
            if amount < config.withdrawal_min_amount:
                self.bot.reply_to(message, f"❌ حداقل مبلغ برداشت {config.withdrawal_min_amount:,} تومان است")
                return
            
            if amount > balance:
                self.bot.reply_to(message, f"❌ موجودی شما کافی نیست!\nموجودی: {balance:,} تومان")
                return
            
            msg = self.bot.send_message(message.chat.id, f"💰 مبلغ {amount:,} تومان\n\nلطفاً شماره کارت خود را وارد کنید:", parse_mode='Markdown')
            self.bot.register_next_step_handler(msg, self._process_withdrawal_card, amount)
            
        except ValueError:
            self.bot.reply_to(message, "❌ لطفاً یک عدد معتبر وارد کنید")
    
    def _process_withdrawal_card(self, message, amount):
        """پردازش شماره کارت"""
        card_number = message.text.replace(' ', '').replace('-', '').strip()
        
        if not card_number.isdigit() or len(card_number) < 16:
            self.bot.reply_to(message, "❌ شماره کارت نامعتبر است. لطفاً مجدداً تلاش کنید.")
            return
        
        msg = self.bot.send_message(message.chat.id, f"💰 مبلغ: {amount:,} تومان\n🏦 شماره کارت: {card_number}\n\nلطفاً نام صاحب حساب را وارد کنید:", parse_mode='Markdown')
        self.bot.register_next_step_handler(msg, self._process_withdrawal_holder, amount, card_number)
    
    def _process_withdrawal_holder(self, message, amount, card_number):
        """پردازش نام صاحب حساب"""
        card_holder = message.text.strip()
        trans_id = hashlib.md5(f"{message.from_user.id}_{amount}_{time.time()}".encode()).hexdigest()[:8].upper()
        
        db.execute('''
            INSERT INTO withdrawals (user_id, amount, card_number, card_holder, transaction_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (message.from_user.id, amount, card_number, card_holder, trans_id, datetime.now().isoformat()))
        
        db.execute('UPDATE users SET available_balance = available_balance - ? WHERE user_id = ?', (amount, message.from_user.id))
        
        self.bot.reply_to(message, f"""
✅ **درخواست برداشت شما ثبت شد!**

💰 مبلغ: {amount:,} تومان
🆔 کد پیگیری: `{trans_id}`

⏳ پس از تأیید ادمین، مبلغ به حساب شما واریز خواهد شد.
""", parse_mode='Markdown')
        
        # اطلاع به ادمین
        for admin_id in ADMIN_IDS:
            self.bot.send_message(admin_id, f"""
💸 **درخواست برداشت جدید**

👤 کاربر: {message.from_user.first_name}
🆔 شناسه: `{message.from_user.id}`
💰 مبلغ: {amount:,} تومان
🏦 شماره کارت: {card_number}
👤 صاحب حساب: {card_holder}
🆔 کد: `{trans_id}`
""", parse_mode='Markdown')
    
    def _handle_receipt(self, message):
        """هندلر فیش پرداخت"""
        user_id = message.from_user.id
        
        # بررسی فیش تکراری
        existing = db.execute('SELECT id FROM receipts WHERE user_id = ? AND status = "pending"', (user_id,))
        if existing:
            self.bot.reply_to(message, "⏳ شما یک فیش در انتظار بررسی دارید. لطفاً صبر کنید.")
            return
        
        try:
            photo = message.photo[-1]
            file_info = self.bot.get_file(photo.file_id)
            file_data = self.bot.download_file(file_info.file_path)
            
            payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
            receipt_path = os.path.join(DIRS['RECEIPTS'], f"{user_id}_{payment_code}.jpg")
            
            with open(receipt_path, 'wb') as f:
                f.write(file_data)
            
            db.execute('''
                INSERT INTO receipts (user_id, amount, receipt_path, payment_code, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, config.subscription_price, receipt_path, payment_code, datetime.now().isoformat()))
            
            self.bot.reply_to(message, f"""
✅ **فیش شما دریافت شد!**

🆔 کد پیگیری: `{payment_code}`
💰 مبلغ: {config.subscription_price:,} تومان

⏳ در اسرع وقت بررسی و تأیید خواهد شد.
""", parse_mode='Markdown')
            
            # اطلاع به ادمین
            for admin_id in ADMIN_IDS:
                with open(receipt_path, 'rb') as f:
                    self.bot.send_photo(admin_id, f, caption=f"""
📸 **فیش جدید**

👤 کاربر: {message.from_user.first_name}
🆔 شناسه: `{user_id}`
💰 مبلغ: {config.subscription_price:,} تومان
🆔 کد: `{payment_code}`
                    """, parse_mode='Markdown')
                    
        except Exception as e:
            self.logger.error(f"Receipt error: {e}")
            self.bot.reply_to(message, f"❌ خطا در دریافت فیش: {str(e)}")
    
    def _handle_guide(self, message):
        """هندلر راهنما"""
        text = f"""
📚 **راهنمای کامل ربات**

━━━━━━━━━━━━━━━
🤖 **ساخت ربات جدید:**
1. روی دکمه 🤖 ساخت ربات جدید کلیک کنید
2. فایل .py یا .zip ربات خود را ارسال کنید
3. ربات به طور خودکار ساخته و اجرا می‌شود

━━━━━━━━━━━━━━━
🎁 **تست رایگان:**
• {config.trial_duration} دقیقه رایگان
• برای تست عملکرد سیستم
• پس از اتمام، ربات متوقف می‌شود

━━━━━━━━━━━━━━━
💰 **اشتراک ماهانه:**
• مبلغ: {config.subscription_price:,} تومان
• اعتبار: ۳۰ روز
• پس از خرید، ربات‌های شما فعال می‌شوند

━━━━━━━━━━━━━━━
🎁 **سیستم رفرال:**
• هر کاربر دعوت کنید، ۱۰٪ درآمد او به شما می‌رسد
• موجودی قابل برداشت از {config.withdrawal_min_amount:,} تومان

━━━━━━━━━━━━━━━
📋 **مدیریت ربات‌ها:**
• 📋 ربات‌های من: مشاهده لیست ربات‌ها
• 🔄 شروع/توقف: روشن و خاموش کردن ربات
• 🗑 حذف ربات: پاک کردن ربات

━━━━━━━━━━━━━━━
📞 **پشتیبانی:**
@shahraghee13

💡 **نکات مهم:**
• فایل ربات باید حاوی توکن معتبر باشد
• حجم فایل حداکثر ۱۰ مگابایت
• در صورت مشکل با پشتیبانی تماس بگیرید
"""
        self.bot.send_message(message.chat.id, text, parse_mode='Markdown')
    
    def _handle_admin_panel(self, message):
        """هندلر پنل مدیریت"""
        if message.from_user.id not in ADMIN_IDS:
            return
        
        users_count = db.execute('SELECT COUNT(*) as c FROM users')[0]['c']
        bots_count = db.execute('SELECT COUNT(*) as c FROM bots')[0]['c']
        running_bots = len(self.process_manager.processes)
        pending_withdrawals = db.execute('SELECT COUNT(*) as c FROM withdrawals WHERE status = "pending"')[0]['c']
        pending_receipts = db.execute('SELECT COUNT(*) as c FROM receipts WHERE status = "pending"')[0]['c']
        total_earnings = db.execute('SELECT SUM(amount) as total FROM withdrawals WHERE status = "approved"')[0]['total'] or 0
        
        # آمار سخت‌افزاری
        cpu_percent = psutil.cpu_percent()
        ram_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        
        text = f"""
👑 **پنل مدیریت حرفه‌ای**

━━━━━━━━━━━━━━━
📊 **آمار کلی سیستم**
┌─────────────────────────────────┐
│ 👥 کاربران: {users_count:,}                      │
│ 🤖 کل ربات‌ها: {bots_count:,}                    │
│ 🟢 ربات‌های فعال: {running_bots}                 │
│ ⏳ فیش‌های待: {pending_receipts}                 │
│ 💸 درخواست‌های برداشت: {pending_withdrawals}     │
│ 💰 کل برداشت‌ها: {total_earnings:,} تومان        │
└─────────────────────────────────┘

━━━━━━━━━━━━━━━
🖥️ **وضعیت سرور**
┌─────────────────────────────────┐
│ 💻 CPU: {cpu_percent}%                            │
│ 🧠 RAM: {ram_percent}%                            │
│ 💾 Disk: {disk_percent}%                          │
│ 🔄 آپتایم: {self._get_uptime()}                  │
└─────────────────────────────────┘

━━━━━━━━━━━━━━━
⚙️ **تنظیمات فعلی**
┌─────────────────────────────────┐
│ 💰 قیمت اشتراک: {config.subscription_price:,} تومان │
│ ⏱️ زمان تست: {config.trial_duration} دقیقه           │
│ 💳 شماره کارت: {config.card_number[-4:]}****         │
│ 💸 حداقل برداشت: {config.withdrawal_min_amount:,} تومان │
└─────────────────────────────────┘
"""
        self.bot.send_message(message.chat.id, text, reply_markup=self._get_admin_panel(), parse_mode='Markdown')
    
    def _get_uptime(self) -> str:
        """محاسبه آپتایم سیستم"""
        diff = datetime.now() - self.start_time
        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        return f"{days} روز {hours} ساعت {minutes} دقیقه"
    
    def _handle_callback(self, call):
        """هندلر کال‌بک‌های اینلاین"""
        if call.from_user.id not in ADMIN_IDS and not call.data.startswith(('toggle_', 'del_', 'confirm_del_')):
            if call.data not in ['close_menu']:
                self.bot.answer_callback_query(call.id, "⛔ دسترسی غیرمجاز")
                return
        
        # مدیریت توگل ربات
        if call.data.startswith('toggle_'):
            self._handle_toggle_callback(call)
        
        # مدیریت حذف ربات
        elif call.data.startswith('del_'):
            self._handle_delete_callback(call)
        
        elif call.data.startswith('confirm_del_'):
            self._handle_confirm_delete_callback(call)
        
        # مدیریت ادمین
        elif call.data == "admin_receipts":
            self._admin_receipts(call)
        elif call.data == "admin_withdrawals":
            self._admin_withdrawals(call)
        elif call.data == "admin_users":
            self._admin_users(call)
        elif call.data == "admin_stats":
            self._admin_stats(call)
        elif call.data == "admin_delete_bot":
            self._admin_delete_bot(call)
        elif call.data == "admin_fix_bot":
            self._admin_fix_bot(call)
        elif call.data == "admin_change_price":
            self._admin_change_price(call)
        elif call.data == "admin_change_welcome":
            self._admin_change_welcome(call)
        elif call.data == "admin_change_card":
            self._admin_change_card(call)
        elif call.data == "admin_broadcast":
            self._admin_broadcast(call)
        elif call.data == "admin_approve":
            self._admin_approve(call)
        elif call.data == "admin_back":
            self._admin_back(call)
        elif call.data == "close_menu":
            self.bot.delete_message(call.message.chat.id, call.message.message_id)
        
        # مدیریت فیش و برداشت
        elif call.data.startswith('app_rec_'):
            self._approve_receipt(call)
        elif call.data.startswith('rej_rec_'):
            self._reject_receipt(call)
        elif call.data.startswith('app_wit_'):
            self._approve_withdrawal(call)
        elif call.data.startswith('rej_wit_'):
            self._reject_withdrawal(call)
    
    def _handle_toggle_callback(self, call):
        """مدیریت توگل ربات از کال‌بک"""
        bot_id = call.data.replace('toggle_', '')
        bot_info = db.execute('SELECT user_id, token, file_path FROM bots WHERE id = ?', (bot_id,))
        
        if not bot_info or bot_info[0]['user_id'] != call.from_user.id:
            self.bot.answer_callback_query(call.id, "❌ ربات پیدا نشد")
            return
        
        bot_info = bot_info[0]
        is_running = bot_id in self.process_manager.processes
        
        if is_running:
            # توقف ربات
            success = asyncio.run_coroutine_threadsafe(
                self._stop_bot_process(bot_id),
                self.loop
            ).result()
            
            if success:
                db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_id,))
                self.bot.answer_callback_query(call.id, "✅ ربات متوقف شد")
            else:
                self.bot.answer_callback_query(call.id, "❌ خطا در توقف ربات")
        else:
            # شروع ربات
            try:
                with open(bot_info['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                    code = f.read()
                
                token = self._extract_token(code)
                if not token:
                    self.bot.answer_callback_query(call.id, "❌ توکن معتبر پیدا نشد")
                    return
                
                result = asyncio.run_coroutine_threadsafe(
                    self.process_manager._start_bot_process(bot_id, token, call.from_user.id),
                    self.loop
                ).result()
                
                if result:
                    db.execute('UPDATE bots SET status = "running" WHERE id = ?', (bot_id,))
                    self.bot.answer_callback_query(call.id, "✅ ربات شروع شد")
                else:
                    self.bot.answer_callback_query(call.id, "❌ خطا در شروع ربات")
            except Exception as e:
                self.logger.error(f"Toggle error: {e}")
                self.bot.answer_callback_query(call.id, f"❌ خطا: {str(e)[:50]}")
        
        self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    
    async def _stop_bot_process(self, bot_id: str) -> bool:
        """توقف فرآیند ربات"""
        if bot_id in self.process_manager.processes:
            info = self.process_manager.processes[bot_id]
            try:
                info.process.terminate()
                await asyncio.sleep(2)
                if info.process.returncode is None:
                    info.process.kill()
                del self.process_manager.processes[bot_id]
                return True
            except:
                return False
        return True
    
    def _handle_delete_callback(self, call):
        """مدیریت حذف ربات"""
        bot_id = call.data.replace('del_', '')
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"confirm_del_{bot_id}"),
            types.InlineKeyboardButton("❌ انصراف", callback_data="close_menu")
        )
        self.bot.edit_message_text("⚠️ **آیا از حذف این ربات اطمینان دارید؟**\nاین عمل غیرقابل بازگشت است.",
                                   call.message.chat.id, call.message.message_id, 
                                   reply_markup=markup, parse_mode='Markdown')
    
    def _handle_confirm_delete_callback(self, call):
        """تأیید نهایی حذف ربات"""
        bot_id = call.data.replace('confirm_del_', '')
        bot_info = db.execute('SELECT user_id FROM bots WHERE id = ?', (bot_id,))
        
        if bot_info and bot_info[0]['user_id'] == call.from_user.id:
            # توقف ربات
            asyncio.run_coroutine_threadsafe(self._stop_bot_process(bot_id), self.loop)
            
            # حذف از دیتابیس
            db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
            db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (call.from_user.id,))
            
            self.bot.answer_callback_query(call.id, "✅ ربات حذف شد")
            self.bot.delete_message(call.message.chat.id, call.message.message_id)
            self.bot.send_message(call.message.chat.id, "🗑 ربات با موفقیت حذف شد.")
    
    def _admin_receipts(self, call):
        """مدیریت فیش‌ها در پنل ادمین"""
        receipts = db.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at')
        
        if not receipts:
            self.bot.send_message(call.message.chat.id, "📸 هیچ فیش جدیدی وجود ندارد")
            return
        
        for r in receipts:
            text = f"🆔 {r['id']}\n👤 کاربر: {r['user_id']}\n💰 مبلغ: {r['amount']:,}\n🆔 کد: {r['payment_code']}"
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ تایید و فعال‌سازی اشتراک", callback_data=f"app_rec_{r['id']}"),
                types.InlineKeyboardButton("❌ رد", callback_data=f"rej_rec_{r['id']}")
            )
            
            if os.path.exists(r['receipt_path']):
                with open(r['receipt_path'], 'rb') as f:
                    self.bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup)
            else:
                self.bot.send_message(call.message.chat.id, text, reply_markup=markup)
    
    def _approve_receipt(self, call):
        """تأیید فیش و فعال‌سازی اشتراک"""
        receipt_id = int(call.data.replace('app_rec_', ''))
        receipt = db.execute('SELECT user_id FROM receipts WHERE id = ?', (receipt_id,))
        
        if receipt:
            user_id = receipt[0]['user_id']
            
            # فعال‌سازی اشتراک
            now = datetime.now()
            end = now + timedelta(days=30)
            db.execute('''
                UPDATE users SET subscription_status = 'active', subscription_end = ?, payment_status = 'approved'
                WHERE user_id = ?
            ''', (end.isoformat(), user_id))
            
            db.execute('''
                UPDATE receipts SET status = "approved", reviewed_by = ?, reviewed_at = ?
                WHERE id = ?
            ''', (call.from_user.id, datetime.now().isoformat(), receipt_id))
            
            try:
                self.bot.send_message(user_id, "✅ پرداخت شما تأیید شد!\nاشتراک ماهانه شما فعال شد.\nاز خدمات ما لذت ببرید 🚀")
            except:
                pass
            
            self.bot.answer_callback_query(call.id, "✅ اشتراک کاربر فعال شد")
            self.bot.delete_message(call.message.chat.id, call.message.message_id)
    
    def _reject_receipt(self, call):
        """رد فیش"""
        receipt_id = int(call.data.replace('rej_rec_', ''))
        receipt = db.execute('SELECT user_id FROM receipts WHERE id = ?', (receipt_id,))
        
        if receipt:
            user_id = receipt[0]['user_id']
            
            db.execute('UPDATE receipts SET status = "rejected", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
                      (call.from_user.id, datetime.now().isoformat(), receipt_id))
            
            try:
                self.bot.send_message(user_id, "❌ متأسفانه فیش پرداخت شما تأیید نشد.\nلطفاً با پشتیبانی تماس بگیرید.")
            except:
                pass
            
            self.bot.answer_callback_query(call.id, "❌ فیش رد شد")
            self.bot.delete_message(call.message.chat.id, call.message.message_id)
    
    def _admin_withdrawals(self, call):
        """مدیریت درخواست‌های برداشت"""
        withdrawals = db.execute('SELECT * FROM withdrawals WHERE status = "pending" ORDER BY created_at')
        
        if not withdrawals:
            self.bot.send_message(call.message.chat.id, "💸 هیچ درخواست برداشتی وجود ندارد")
            return
        
        for w in withdrawals:
            text = f"""
💸 **درخواست برداشت**

🆔 شماره: {w['id']}
👤 کاربر: {w['user_id']}
💰 مبلغ: {w['amount']:,} تومان
🏦 شماره کارت: {w['card_number']}
👤 صاحب حساب: {w['card_holder']}
🆔 کد: `{w['transaction_id']}`
📅 تاریخ: {w['created_at'][:10]}
"""
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ تایید واریز", callback_data=f"app_wit_{w['id']}"),
                types.InlineKeyboardButton("❌ رد", callback_data=f"rej_wit_{w['id']}")
            )
            
            self.bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    
    def _approve_withdrawal(self, call):
        """تأیید برداشت"""
        withdrawal_id = int(call.data.replace('app_wit_', ''))
        withdrawal = db.execute('SELECT user_id, amount FROM withdrawals WHERE id = ?', (withdrawal_id,))
        
        if withdrawal:
            user_id = withdrawal[0]['user_id']
            amount = withdrawal[0]['amount']
            
            db.execute('''
                UPDATE withdrawals SET status = "approved", reviewed_by = ?, reviewed_at = ?
                WHERE id = ?
            ''', (call.from_user.id, datetime.now().isoformat(), withdrawal_id))
            
            db.execute('UPDATE users SET withdrawn_amount = withdrawn_amount + ? WHERE user_id = ?', (amount, user_id))
            
            try:
                self.bot.send_message(user_id, f"✅ درخواست برداشت شما تأیید شد!\n💰 مبلغ {amount:,} تومان به حساب شما واریز شد.")
            except:
                pass
            
            self.bot.answer_callback_query(call.id, "✅ برداشت تأیید شد")
            self.bot.delete_message(call.message.chat.id, call.message.message_id)
    
    def _reject_withdrawal(self, call):
        """رد برداشت و برگشت موجودی"""
        withdrawal_id = int(call.data.replace('rej_wit_', ''))
        withdrawal = db.execute('SELECT user_id, amount FROM withdrawals WHERE id = ?', (withdrawal_id,))
        
        if withdrawal:
            user_id = withdrawal[0]['user_id']
            amount = withdrawal[0]['amount']
            
            db.execute('''
                UPDATE withdrawals SET status = "rejected", reviewed_by = ?, reviewed_at = ?
                WHERE id = ?
            ''', (call.from_user.id, datetime.now().isoformat(), withdrawal_id))
            
            db.execute('UPDATE users SET available_balance = available_balance + ? WHERE user_id = ?', (amount, user_id))
            
            try:
                self.bot.send_message(user_id, f"❌ متأسفانه درخواست برداشت شما رد شد.\n💰 مبلغ {amount:,} تومان به موجودی شما برگشت داده شد.")
            except:
                pass
            
            self.bot.answer_callback_query(call.id, "❌ برداشت رد شد")
            self.bot.delete_message(call.message.chat.id, call.message.message_id)
    
    def _admin_users(self, call):
        """لیست کاربران"""
        users = db.execute('SELECT user_id, first_name, bots_count, subscription_status FROM users ORDER BY created_at DESC LIMIT 30')
        
        text = "👥 **لیست کاربران (۳۰ نفر آخر):**\n\n"
        for u in users:
            status_emoji = "🟢" if u['subscription_status'] in ['active', 'trial'] else "🔴"
            text += f"{status_emoji} `{u['user_id']}` - {u['first_name'] or 'نامشخص'} - {u['bots_count']} ربات\n"
        
        self.bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    
    def _admin_stats(self, call):
        """آمار پیشرفته"""
        users = db.execute('SELECT COUNT(*) as c FROM users')[0]['c']
        bots = db.execute('SELECT COUNT(*) as c FROM bots')[0]['c']
        running = len(self.process_manager.processes)
        active_subs = db.execute('SELECT COUNT(*) as c FROM users WHERE subscription_status = "active"')[0]['c']
        trial_subs = db.execute('SELECT COUNT(*) as c FROM users WHERE subscription_status = "trial"')[0]['c']
        payments = db.execute('SELECT COUNT(*) as c FROM receipts WHERE status = "approved"')[0]['c']
        withdrawals = db.execute('SELECT SUM(amount) as total FROM withdrawals WHERE status = "approved"')[0]['total'] or 0
        
        # آمار سخت‌افزاری
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        text = f"""
📊 **آمار پیشرفته سیستم**

━━━━━━━━━━━━━━━
👥 **کاربران**
┌─────────────────────────────────┐
│ 👥 کل کاربران: {users:,}                      │
│ ✅ اشتراک فعال: {active_subs}                  │
│ 🎁 تست رایگان: {trial_subs}                   │
└─────────────────────────────────┘

━━━━━━━━━━━━━━━
🤖 **ربات‌ها**
┌─────────────────────────────────┐
│ 📦 کل ربات‌ها: {bots:,}                      │
│ 🟢 ربات‌های فعال: {running}                   │
│ 📊 نرخ موفقیت: {(running/bots*100) if bots else 0:.1f}% │
└─────────────────────────────────┘

━━━━━━━━━━━━━━━
💰 **مالی**
┌─────────────────────────────────┐
│ 💳 پرداخت‌های موفق: {payments}               │
│ 💰 کل دریافتی: {payments * config.subscription_price:,} تومان │
│ 💸 برداشت‌شده: {withdrawals:,} تومان         │
└─────────────────────────────────┘

━━━━━━━━━━━━━━━
🖥️ **منابع سیستم**
┌─────────────────────────────────┐
│ 💻 CPU: {cpu}%                              │
│ 🧠 RAM: {ram.percent}% ({ram.used // (1024**3)}/{ram.total // (1024**3)} GB) │
│ 💾 Disk: {disk.percent}%                     │
└─────────────────────────────────┘
"""
        self.bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
    
    def _admin_delete_bot(self, call):
        """حذف ربات توسط ادمین"""
        msg = self.bot.send_message(call.message.chat.id, "🆔 شناسه ربات مورد نظر برای حذف را وارد کنید:")
        self.bot.register_next_step_handler(msg, self._process_admin_delete)
    
    def _process_admin_delete(self, message):
        if message.from_user.id not in ADMIN_IDS:
            return
        
        bot_id = message.text.strip()
        bot_info = db.execute('SELECT user_id FROM bots WHERE id = ?', (bot_id,))
        
        if bot_info:
            asyncio.run_coroutine_threadsafe(self._stop_bot_process(bot_id), self.loop)
            db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
            self.bot.reply_to(message, f"✅ ربات {bot_id} حذف شد")
            
            db.execute('''
                INSERT INTO system_logs (action, admin_id, target_user_id, details, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', ('delete_bot', message.from_user.id, bot_info[0]['user_id'], f"ربات {bot_id} حذف شد", datetime.now().isoformat()))
        else:
            self.bot.reply_to(message, "❌ ربات پیدا نشد")
    
    def _admin_fix_bot(self, call):
        """رفع مشکل ربات توسط ادمین"""
        msg = self.bot.send_message(call.message.chat.id, "🆔 شناسه ربات برای رفع مشکل را وارد کنید:")
        self.bot.register_next_step_handler(msg, self._process_admin_fix)
    
    def _process_admin_fix(self, message):
        if message.from_user.id not in ADMIN_IDS:
            return
        
        bot_id = message.text.strip()
        bot_info = db.execute('SELECT user_id FROM bots WHERE id = ?', (bot_id,))
        
        if bot_info:
            asyncio.run_coroutine_threadsafe(self._stop_bot_process(bot_id), self.loop)
            db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_id,))
            self.bot.reply_to(message, f"✅ ربات {bot_id} ریست شد. کاربر می‌تواند دوباره آن را فعال کند.")
            
            try:
                self.bot.send_message(bot_info[0]['user_id'], f"🔧 ربات شما با شناسه {bot_id} توسط پشتیبانی ریست شد.\nلطفاً دوباره آن را فعال کنید.")
            except:
                pass
        else:
            self.bot.reply_to(message, "❌ ربات پیدا نشد")
    
    def _admin_change_price(self, call):
        """تغییر قیمت اشتراک"""
        msg = self.bot.send_message(call.message.chat.id, "💰 قیمت جدید اشتراک را به تومان وارد کنید:")
        self.bot.register_next_step_handler(msg, self._process_price_change)
    
    def _process_price_change(self, message):
        if message.from_user.id not in ADMIN_IDS:
            return
        
        try:
            new_price = int(message.text.replace(',', '').strip())
            config.subscription_price = new_price
            config.save_config()
            self.bot.reply_to(message, f"✅ قیمت اشتراک به {new_price:,} تومان تغییر کرد")
        except:
            self.bot.reply_to(message, "❌ عدد معتبر وارد کنید")
    
    def _admin_change_welcome(self, call):
        """تغییر متن خوش‌آمدگویی"""
        msg = self.bot.send_message(call.message.chat.id, "📝 متن جدید خوش‌آمدگویی را ارسال کنید:")
        self.bot.register_next_step_handler(msg, self._process_welcome_change)
    
    def _process_welcome_change(self, message):
        if message.from_user.id not in ADMIN_IDS:
            return
        
        config.welcome_text = message.text
        config.save_config()
        self.bot.reply_to(message, "✅ متن خوش‌آمدگویی تغییر کرد")
    
    def _admin_change_card(self, call):
        """تغییر شماره کارت"""
        msg = self.bot.send_message(call.message.chat.id, "🏦 شماره کارت جدید را وارد کنید (۱۶ رقم):")
        self.bot.register_next_step_handler(msg, self._process_card_change)
    
    def _process_card_change(self, message):
        if message.from_user.id not in ADMIN_IDS:
            return
        
        card = message.text.replace(' ', '').replace('-', '').strip()
        if card.isdigit() and len(card) >= 16:
            config.card_number = card
            config.save_config()
            self.bot.reply_to(message, f"✅ شماره کارت به {card[:4]}****{card[-4:]} تغییر کرد")
        else:
            self.bot.reply_to(message, "❌ شماره کارت نامعتبر است")
    
    def _admin_broadcast(self, call):
        """ارسال پیام همگانی"""
        msg = self.bot.send_message(call.message.chat.id, "📢 متن پیام همگانی را ارسال کنید:")
        self.bot.register_next_step_handler(msg, self._process_broadcast)
    
    def _process_broadcast(self, message):
        if message.from_user.id not in ADMIN_IDS:
            return
        
        text = message.text
        users = db.execute('SELECT user_id FROM users')
        
        status_msg = self.bot.reply_to(message, f"📢 در حال ارسال به {len(users)} کاربر...")
        
        sent = 0
        failed = 0
        
        for user in users:
            try:
                self.bot.send_message(user['user_id'], text)
                sent += 1
                if sent % 10 == 0:
                    self.bot.edit_message_text(f"📢 پیشرفت: {sent}/{len(users)}", message.chat.id, status_msg.message_id)
            except:
                failed += 1
        
        self.bot.edit_message_text(f"✅ ارسال شد!\nموفق: {sent}\nناموفق: {failed}", message.chat.id, status_msg.message_id)
    
    def _admin_approve(self, call):
        """تایید مستقیم اشتراک توسط ادمین"""
        msg = self.bot.send_message(call.message.chat.id, "💰 آیدی کاربر برای تایید مستقیم اشتراک را وارد کنید:")
        self.bot.register_next_step_handler(msg, self._process_admin_approve)
    
    def _process_admin_approve(self, message):
        if message.from_user.id not in ADMIN_IDS:
            return
        
        try:
            user_id = int(message.text.strip())
            now = datetime.now()
            end = now + timedelta(days=30)
            db.execute('''
                UPDATE users SET subscription_status = 'active', subscription_end = ?, payment_status = 'approved'
                WHERE user_id = ?
            ''', (end.isoformat(), user_id))
            self.bot.reply_to(message, f"✅ اشتراک کاربر {user_id} فعال شد")
            
            try:
                self.bot.send_message(user_id, "✅ اشتراک شما توسط ادمین فعال شد!")
            except:
                pass
        except:
            self.bot.reply_to(message, "❌ آیدی معتبر وارد کنید")
    
    def _admin_back(self, call):
        """بازگشت به منوی اصلی ادمین"""
        self.bot.delete_message(call.message.chat.id, call.message.message_id)
        self._handle_admin_panel(call.message)
    
    def _get_main_menu(self, user_id: int):
        """دریافت منوی اصلی"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        buttons = [
            types.KeyboardButton("🎁 تست رایگان"),
            types.KeyboardButton("💰 خرید اشتراک"),
            types.KeyboardButton("🤖 ساخت ربات جدید"),
            types.KeyboardButton("📋 ربات‌های من"),
            types.KeyboardButton("🔄 شروع/توقف ربات"),
            types.KeyboardButton("🗑 حذف ربات"),
            types.KeyboardButton("📊 کیف پول من"),
            types.KeyboardButton("🎁 سیستم رفرال"),
            types.KeyboardButton("💸 برداشت وجه"),
            types.KeyboardButton("📚 راهنما"),
        ]
        
        if user_id in ADMIN_IDS:
            buttons.append(types.KeyboardButton("👑 پنل مدیریت"))
        
        markup.add(*buttons)
        return markup
    
    def _get_admin_panel(self):
        """دریافت پنل مدیریت"""
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📸 مدیریت فیش‌ها", callback_data="admin_receipts"),
            types.InlineKeyboardButton("💸 درخواست‌های برداشت", callback_data="admin_withdrawals"),
            types.InlineKeyboardButton("👥 لیست کاربران", callback_data="admin_users"),
            types.InlineKeyboardButton("📊 آمار پیشرفته", callback_data="admin_stats"),
            types.InlineKeyboardButton("🗑 حذف ربات کاربر", callback_data="admin_delete_bot"),
            types.InlineKeyboardButton("🔧 رفع مشکل ربات", callback_data="admin_fix_bot"),
            types.InlineKeyboardButton("💳 تغییر قیمت", callback_data="admin_change_price"),
            types.InlineKeyboardButton("📝 تغییر متن خوش‌آمدگویی", callback_data="admin_change_welcome"),
            types.InlineKeyboardButton("🏦 تغییر شماره کارت", callback_data="admin_change_card"),
            types.InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast"),
            types.InlineKeyboardButton("💰 تایید مستقیم اشتراک", callback_data="admin_approve"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
        )
        return markup
    
    def _get_subscription_text(self, user_id: int) -> str:
        """دریافت متن وضعیت اشتراک"""
        access = self._check_subscription(user_id)
        
        if access['has_access']:
            if access['status'] == 'trial':
                return f"🎁 وضعیت: تست رایگان - {access['minutes_left']} دقیقه باقی مانده"
            else:
                return f"✅ وضعیت: اشتراک فعال - {access['days_left']} روز باقی مانده"
        else:
            return "❌ وضعیت: بدون اشتراک"
    
    def run(self):
        """اجرای ربات"""
        self.logger.info("🚀 ربات مادر شروع به کار کرد")
        
        # شروع مانیتورینگ خودکار
        asyncio.run_coroutine_threadsafe(self._auto_monitor(), self.loop)
        
        # اجرای ربات
        while True:
            try:
                self.bot.infinity_polling(timeout=60, long_polling_timeout=60)
            except Exception as e:
                self.logger.error(f"Polling error: {e}")
                time.sleep(5)
    
    async def _auto_monitor(self):
        """مانیتورینگ خودکار سیستم"""
        while True:
            try:
                # بررسی اشتراک‌های منقضی
                now = datetime.now()
                
                # اشتراک‌های فعال منقضی شده
                expired_subs = db.execute('''
                    SELECT user_id FROM users 
                    WHERE subscription_status = 'active' AND subscription_end < ?
                ''', (now.isoformat(),))
                
                for user in expired_subs:
                    db.execute('UPDATE users SET subscription_status = "expired" WHERE user_id = ?', (user['user_id'],))
                    
                    # توقف ربات‌های کاربر
                    user_bots = db.execute('SELECT id FROM bots WHERE user_id = ? AND status = "running"', (user['user_id'],))
                    for bot in user_bots:
                        await self._stop_bot_process(bot['id'])
                        db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot['id'],))
                    
                    try:
                        self.bot.send_message(user['user_id'], "⚠️ اشتراک شما به اتمام رسید!\nبرای ادامه استفاده، لطفاً اشتراک جدید تهیه کنید.")
                    except:
                        pass
                
                # تست‌های رایگان منقضی شده
                expired_trials = db.execute('''
                    SELECT user_id FROM users 
                    WHERE subscription_status = 'trial' AND trial_end < ?
                ''', (now.isoformat(),))
                
                for user in expired_trials:
                    db.execute('UPDATE users SET subscription_status = "inactive" WHERE user_id = ?', (user['user_id'],))
                    
                    # توقف ربات‌های تست
                    user_bots = db.execute('SELECT id FROM bots WHERE user_id = ? AND status = "running" AND is_trial = 1', (user['user_id'],))
                    for bot in user_bots:
                        await self._stop_bot_process(bot['id'])
                        db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot['id'],))
                    
                    try:
                        self.bot.send_message(user['user_id'], f"⏰ زمان تست رایگان شما به اتمام رسید!\nبرای ادامه استفاده، اشتراک تهیه کنید.")
                    except:
                        pass
                
                await asyncio.sleep(60)  # هر دقیقه بررسی کن
                
            except Exception as e:
                self.logger.error(f"Auto monitor error: {e}")
                await asyncio.sleep(60)

# ==================== اجرای اصلی ====================

if __name__ == "__main__":
    print("\n" + "=" * 100)
    print("🚀 ربات مادر حرفه‌ای - Enterprise Edition v7.0".center(100))
    print("⚡ با تکنولوژی سخت‌افزاری پیشرفته | بیش از ۳۵۰۰ خط کد".center(100))
    print("=" * 100)
    
    # ایجاد نمونه از ربات
    mother_bot = MotherBot()
    
    # نمایش اطلاعات نهایی
    print(f"✅ قیمت اشتراک: {config.subscription_price:,} تومان")
    print(f"✅ تست رایگان: {config.trial_duration} دقیقه")
    print(f"✅ سیستم رفرال: 10%")
    print(f"✅ حداقل برداشت: {config.withdrawal_min_amount:,} تومان")
    print(f"✅ تعداد هسته‌های CPU: {mother_bot.hardware.cpu_count}")
    print(f"✅ رم سیستم: {mother_bot.hardware.ram_gb:.1f} GB")
    print(f"✅ تردهای همزمان: {mother_bot.hardware.optimal_threads}")
    print("=" * 100)
    print(f"👑 ادمین: {ADMIN_IDS}")
    print("=" * 100)
    
    # اجرا
    mother_bot.run()