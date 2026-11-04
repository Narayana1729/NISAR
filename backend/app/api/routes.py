from fastapi import APIRouter
from app.api.endpoints import datasets, domain1, domain2, domain3, domain4, domain5, explorer, health

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["Datasets"])
api_router.include_router(domain1.router, prefix="/domains/domain1", tags=["Domain 1: Floods & Wetlands"])
api_router.include_router(domain2.router, prefix="/domains/domain2", tags=["Domain 2: Forests & Wildfires"])
api_router.include_router(domain3.router, prefix="/domains/domain3", tags=["Domain 3: Earthquakes & Ground Deformation"])
api_router.include_router(domain4.router, prefix="/domains/domain4", tags=["Domain 4: Agriculture & Soil Conditions"])
api_router.include_router(domain5.router, prefix="/domains/domain5", tags=["Domain 5: Glaciers & Snow/Ice"])
api_router.include_router(domain1.router, prefix="/domain1", tags=["Domain 1: Floods & Wetlands (Direct Alias)"])
api_router.include_router(domain2.router, prefix="/domain2", tags=["Domain 2: Forests & Wildfires (Direct Alias)"])
api_router.include_router(domain3.router, prefix="/domain3", tags=["Domain 3: Earthquakes & Ground Deformation (Direct Alias)"])
api_router.include_router(domain4.router, prefix="/domain4", tags=["Domain 4: Agriculture & Soil Conditions (Direct Alias)"])
api_router.include_router(domain5.router, prefix="/domain5", tags=["Domain 5: Glaciers & Snow/Ice (Direct Alias)"])
api_router.include_router(explorer.router, prefix="/explorer", tags=["Domain 6: Earth Event Explorer"])
api_router.include_router(explorer.router, prefix="", tags=["Explorer & Runs Direct Alias"])
