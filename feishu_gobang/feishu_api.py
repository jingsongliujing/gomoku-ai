"""
飞书多维表格API模块
"""

import os
import requests
import json
import time
from typing import Dict, List, Optional, Any

from . import config


class FeishuAPI:
    """飞书API封装类"""
    
    def __init__(self):
        self.app_id = config.FEISHU_APP_ID
        self.app_secret = config.FEISHU_APP_SECRET
        self.base_url = config.FEISHU_API_BASE
        self.tenant_access_token = None
        self.token_expires_at = 0
        
    def _get_tenant_access_token(self) -> str:
        """获取tenant_access_token"""
        if self.tenant_access_token and time.time() < self.token_expires_at:
            return self.tenant_access_token
            
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        response = requests.post(url, json=payload)
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"获取token失败: {data.get('msg')}")
            
        self.tenant_access_token = data["tenant_access_token"]
        self.token_expires_at = time.time() + data.get("expire", 7200) - 300  # 提前5分钟刷新
        
        return self.tenant_access_token
        
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        token = self._get_tenant_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
    def get_bitable_app_token(self, wiki_token: str) -> str:
        """从wiki token获取bitable的app_token"""
        url = f"{self.base_url}/wiki/v2/spaces/get_node"
        params = {"token": wiki_token}
        
        response = requests.get(url, headers=self._get_headers(), params=params)
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"获取wiki节点信息失败: {data.get('msg')}")
            
        node = data.get("data", {}).get("node", {})
        obj_token = node.get("obj_token")
        
        if not obj_token:
            raise Exception("无法获取bitable的app_token")
            
        return obj_token
        
    def list_tables(self, app_token: str) -> List[Dict[str, Any]]:
        """获取数据表列表"""
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables"
        
        response = requests.get(url, headers=self._get_headers())
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"获取数据表列表失败: {data.get('msg')}")
            
        return data.get("data", {}).get("items", [])
        
    def create_table(self, app_token: str, table_name: str, fields: List[Dict[str, Any]]) -> str:
        """创建数据表"""
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables"
        payload = {
            "table": {
                "name": table_name,
                "fields": fields
            }
        }
        
        response = requests.post(url, headers=self._get_headers(), json=payload)
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"创建数据表失败: {data.get('msg')}")
            
        return data.get("data", {}).get("table_id")
        
    def list_fields(self, app_token: str, table_id: str) -> List[Dict[str, Any]]:
        """获取数据表的字段列表"""
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
        
        response = requests.get(url, headers=self._get_headers())
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"获取字段列表失败: {data.get('msg')}")
            
        return data.get("data", {}).get("items", [])
        
    def create_field(self, app_token: str, table_id: str, field_name: str, 
                    field_type: int, property: Optional[Dict[str, Any]] = None) -> str:
        """
        创建字段
        
        Args:
            app_token: 多维表格token
            table_id: 数据表ID
            field_name: 字段名称
            field_type: 字段类型 (1=文本, 2=数字, 3=单选, 5=日期, 7=复选框, 11=人员, 13=电话, 15=超链接, 17=附件, 18=关联, 20=公式, 21=双向关联, 22=地理位置, 23=群组, 1001=创建时间, 1002=更新时间, 1003=创建人, 1004=更新人)
            property: 字段属性（如单选选项）
            
        Returns:
            字段ID
        """
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
        payload = {
            "field_name": field_name,
            "type": field_type
        }
        if property:
            payload["property"] = property
            
        response = requests.post(url, headers=self._get_headers(), json=payload)
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"创建字段失败: {data.get('msg')}")
            
        return data.get("data", {}).get("field", {}).get("field_id")
        
    def update_field(self, app_token: str, table_id: str, field_id: str,
                    field_name: str, field_type: int, 
                    property: Optional[Dict[str, Any]] = None) -> bool:
        """更新字段"""
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}"
        payload = {
            "field_name": field_name,
            "type": field_type
        }
        if property:
            payload["property"] = property
            
        response = requests.put(url, headers=self._get_headers(), json=payload)
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"更新字段失败: {data.get('msg')}")
            
        return True
        
    def get_records(self, app_token: str, table_id: str, 
                    filter_expr: Optional[str] = None,
                    page_size: int = 100,
                    page_token: Optional[str] = None) -> Dict[str, Any]:
        """获取记录列表"""
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/records"
        params = {"page_size": page_size}
        
        if filter_expr:
            params["filter"] = filter_expr
        if page_token:
            params["page_token"] = page_token
            
        response = requests.get(url, headers=self._get_headers(), params=params)
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"获取记录失败: {data.get('msg')}")
            
        return data.get("data", {})
        
    def get_all_records(self, app_token: str, table_id: str,
                        filter_expr: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有记录（自动分页）"""
        all_records = []
        page_token = None
        
        while True:
            data = self.get_records(app_token, table_id, filter_expr, 
                                   page_size=100, page_token=page_token)
            items = data.get("items") or []
            all_records.extend(items)
            
            if not data.get("has_more"):
                break
            page_token = data.get("page_token")
            
        return all_records
        
    def get_record(self, app_token: str, table_id: str, record_id: str) -> Dict[str, Any]:
        """获取单条记录"""
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
        
        response = requests.get(url, headers=self._get_headers())
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"获取记录失败: {data.get('msg')}")
            
        return data.get("data", {}).get("record", {})
        
    def create_record(self, app_token: str, table_id: str, fields: Dict[str, Any]) -> str:
        """创建记录"""
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/records"
        payload = {"fields": fields}
        
        response = requests.post(url, headers=self._get_headers(), json=payload)
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"创建记录失败: {data.get('msg')}")
            
        return data.get("data", {}).get("record", {}).get("record_id")
        
    def create_records_batch(self, app_token: str, table_id: str, 
                            records: List[Dict[str, Any]]) -> List[str]:
        """批量创建记录"""
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
        payload = {"records": [{"fields": r} for r in records]}
        
        response = requests.post(url, headers=self._get_headers(), json=payload)
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"批量创建记录失败: {data.get('msg')}")
            
        return [r.get("record_id") for r in data.get("data", {}).get("records", [])]
        
    def update_record(self, app_token: str, table_id: str, 
                     record_id: str, fields: Dict[str, Any]) -> bool:
        """更新记录"""
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
        payload = {"fields": fields}
        
        response = requests.put(url, headers=self._get_headers(), json=payload)
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"更新记录失败: {data.get('msg')}")
            
        return True
        
    def update_records_batch(self, app_token: str, table_id: str,
                            records: List[Dict[str, Any]]) -> bool:
        """批量更新记录"""
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_update"
        payload = {"records": records}
        
        response = requests.post(url, headers=self._get_headers(), json=payload)
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"批量更新记录失败: {data.get('msg')}")
            
        return True
        
    def delete_record(self, app_token: str, table_id: str, record_id: str) -> bool:
        """删除记录"""
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
        
        response = requests.delete(url, headers=self._get_headers())
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"删除记录失败: {data.get('msg')}")
            
        return True
        
    def upload_image(self, app_token: str, table_id: str, 
                    record_id: str, field_name: str, 
                    image_path: str) -> bool:
        """
        上传图片到记录的附件字段
        
        Args:
            app_token: 多维表格token
            table_id: 数据表ID
            record_id: 记录ID
            field_name: 附件字段名
            image_path: 图片文件路径
            
        Returns:
            是否成功
        """
        # 首先上传文件获取file_token
        upload_url = f"{self.base_url}/drive/v1/medias/upload_all"
        
        file_size = os.path.getsize(image_path)
        file_name = os.path.basename(image_path)
        
        with open(image_path, 'rb') as f:
            files = {
                'file': (file_name, f, 'image/png'),
            }
            data = {
                'file_name': file_name,
                'parent_type': 'bitable_image',
                'parent_node': app_token,
                'size': str(file_size)
            }
            
            response = requests.post(
                upload_url, 
                headers={"Authorization": f"Bearer {self._get_tenant_access_token()}"},
                files=files,
                data=data
            )
            
        result = response.json()
        if result.get("code") != 0:
            raise Exception(f"上传文件失败: {result.get('msg')}")
            
        file_token = result.get("data", {}).get("file_token")
        
        # 更新记录的附件字段
        update_url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
        payload = {
            "fields": {
                field_name: [{"file_token": file_token}]
            }
        }
        
        response = requests.put(update_url, headers=self._get_headers(), json=payload)
        result = response.json()
        
        if result.get("code") != 0:
            raise Exception(f"更新记录失败: {result.get('msg')}")
            
        return True
