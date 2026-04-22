import uuid
from typing import Any, Dict

from .ids import IdGenerator


class ProjectBuilder:
    """Build ToP project and archive metadata."""

    def __init__(self, id_generator: IdGenerator):
        self.id_generator = id_generator

    def create_project(self, project_id: str) -> Dict[str, Any]:
        return {
            "coverPath": "",
            "createBy": "admin",
            "delFlag": "0",
            "groupId": self.id_generator.generate_project_id(),
            "id": project_id,
            "orderNo": 0,
            "projectName": "nick11",
            "publicFlag": "0",
            "unitSetId": "default",
            "updateTime": "2026-02-03 02:13:54"
        }

    def create_archive(self, project_id: str, process_id: str) -> Dict[str, Any]:
        return {
            "createTime": "2026-02-04 06:37:43",
            "currentFlag": 1,
            "id": "2018936993196044289",
            "processId": process_id,
            "projectId": project_id,
            "runStatus": 0,
            "syncGraphVersion": 23,
            "syncParamVersion": 22,
            "updateTime": "2026-02-04 06:37:43",
            "uuid": str(uuid.uuid4()).replace("-", ""),
            "versionNo": "latest"
        }
