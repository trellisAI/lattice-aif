from latticepy.server import LatticeTool, LatticeTool


from pydantic import BaseModel, Field
import os

class CpuData(BaseModel):
    os: str = Field(..., description="the operating sytem")

@LatticeTool(description="Calculates the square root of a positive number.",
        schema=CpuData.model_json_schema(),
        return_desc="return the details about the cpu of the machine")
def get_cpu_details():
    print(os.platform)

