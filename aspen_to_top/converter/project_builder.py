import uuid
from typing import Any, Dict

from .ids import IdGenerator


class ProjectBuilder:
    """构建 ToP 工程和归档元信息。

    这些字段大多不是 Aspen 文件中的流程数据，而是 ToP 导入 JSON 需要的
    工程壳信息。后续如果要调整工程名称、默认用户、版本号等固定字段，
    应该集中改这个文件，而不要散落到图构建或 Aspen 读取逻辑里。
    """

    def __init__(self, id_generator: IdGenerator):
        self.id_generator = id_generator

    def create_project(self, project_id: str) -> Dict[str, Any]:
        """生成 omProject。

        project_id 由上层统一生成，并会被组分、物性方法、归档信息引用。
        groupId 目前只需要满足 ToP 导入格式，因此每次随机生成。
        """
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
        """生成 omProcessArchive。

        processId 必须和 omProcessGraph.id 保持一致；projectId 必须和
        omProject.id 保持一致。uuid 是 ToP 归档内部标识，每次转换生成新值。
        """
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
