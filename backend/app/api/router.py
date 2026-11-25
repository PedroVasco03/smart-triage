from fastapi import APIRouter

from app.api import agent, patients, queue, resources, simulation, statistics

api_router = APIRouter()
for module in (patients, agent, queue, simulation, statistics, resources):
    api_router.include_router(module.router)
