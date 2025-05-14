import os
import psutil
import platform
import time
import logging
from typing import Dict, List, Any, Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MonitorService:
    """服务用于监控系统性能指标"""
    
    def __init__(self):
        self.history = {
            'cpu': [],
            'memory': [],
            'disk': [],
            'network': []
        }
        self.max_history_points = 60  # 保存最近60个数据点

        # 预热 psutil.cpu_percent 调用
        # 这些首次调用会返回 0.0 或 [0.0,...] 并为后续非阻塞调用建立基准
        psutil.cpu_percent(interval=None)
        psutil.cpu_percent(interval=None, percpu=True)
        # 短暂休眠，确保第一次实际度量时有时间流逝
        time.sleep(0.05)
    
    def get_system_info(self) -> Dict:
        """获取系统基本信息"""
        info = {
            'system': platform.system(),
            'node': platform.node(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'cpu_count': psutil.cpu_count(logical=False),
            'cpu_count_logical': psutil.cpu_count(logical=True),
            'memory_total': psutil.virtual_memory().total,
            'boot_time': psutil.boot_time()
        }
        return info
    
    def get_current_metrics(self) -> Dict:
        """获取当前系统指标"""
        # 使用 interval=None 进行非阻塞调用
        # 这将返回自上次调用（或__init__中的预热调用）以来的CPU使用百分比
        cpu_percent_val = psutil.cpu_percent(interval=None)
        per_cpu_val = psutil.cpu_percent(interval=None, percpu=True)
        
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net_io = psutil.net_io_counters()
        
        metrics = {
            'timestamp': time.time(),
            'cpu': {
                'percent': cpu_percent_val,
                'per_cpu': per_cpu_val
            },
            'memory': {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'percent': memory.percent
            },
            'disk': {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk.percent
            },
            'network': {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            }
        }
        
        # 更新历史数据
        self._update_history(metrics)
        
        return metrics
    
    def get_process_info(self, include_python_only: bool = False) -> List[Dict]:
        """获取进程信息"""
        processes = []
        
        try:
            # 首先尝试使用标准方式获取所有进程
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'create_time']):
                try:
                    pinfo = proc.info
                    
                    # 处理可能存在的None值
                    if pinfo['cpu_percent'] is None:
                        pinfo['cpu_percent'] = 0.0
                    
                    if pinfo['memory_percent'] is None:
                        pinfo['memory_percent'] = 0.0
                    
                    if pinfo['create_time'] is None:
                        pinfo['create_time'] = 0.0
                    
                    # 仅包含Python进程（可选）
                    if include_python_only and 'python' not in str(pinfo['name']).lower():
                        continue
                    
                    processes.append({
                        'pid': pinfo['pid'],
                        'name': pinfo.get('name', 'unknown'),
                        'username': pinfo.get('username', 'unknown'),
                        'cpu_percent': float(pinfo['cpu_percent']),
                        'memory_percent': float(pinfo['memory_percent']),
                        'create_time': float(pinfo['create_time'])
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
                except Exception as e:
                    logger.error(f"处理进程信息时出错: {str(e)}")
        
            # 如果没有获取到任何进程信息（可能是权限问题），尝试只获取当前用户的进程
            if len(processes) == 0:
                logger.warning("无法获取所有进程信息，尝试只获取当前用户的进程")
                import os
                try:
                    current_user = os.getlogin()
                except:
                    current_user = 'current'
                
                for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'create_time']):
                    try:
                        pinfo = proc.info
                        
                        # 只包含当前用户的进程
                        if pinfo['username'] != current_user:
                            continue
                        
                        # 仅包含Python进程（可选）
                        if include_python_only and 'python' not in str(pinfo['name']).lower():
                            continue
                        
                        processes.append({
                            'pid': pinfo['pid'],
                            'name': pinfo.get('name', 'unknown'),
                            'username': pinfo.get('username', 'unknown'),
                            'cpu_percent': float(pinfo['cpu_percent']),
                            'memory_percent': float(pinfo['memory_percent']),
                            'create_time': float(pinfo['create_time'])
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
                    except Exception as e:
                        logger.error(f"处理当前用户进程信息时出错: {str(e)}")
        except Exception as e:
            logger.error(f"获取进程信息时发生错误: {str(e)}")
            # 返回至少一个进程的信息 - 当前Python进程
            try:
                current_process = psutil.Process()
                with current_process.oneshot():
                    cpu_percent = current_process.cpu_percent() or 0.0
                    memory_percent = current_process.memory_percent() or 0.0
                    create_time = current_process.create_time() or 0.0
                    
                    processes.append({
                        'pid': current_process.pid,
                        'name': current_process.name(),
                        'username': current_process.username(),
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory_percent,
                        'create_time': create_time
                    })
            except Exception as inner_e:
                logger.error(f"获取当前进程信息时出错: {str(inner_e)}")
                # 返回一个占位进程信息
                processes.append({
                    'pid': 0,
                    'name': 'system',
                    'username': 'system',
                    'cpu_percent': 0.0,
                    'memory_percent': 0.0,
                    'create_time': 0.0
                })
        
        # 按CPU使用率排序
        return sorted(processes, key=lambda x: x['cpu_percent'] or 0.0, reverse=True)
    
    def get_history(self, metric_type: str = None, points: int = None) -> Dict:
        """获取历史性能数据"""
        if metric_type is not None:
            if metric_type not in self.history:
                raise ValueError(f"Invalid metric type: {metric_type}")
            
            data = self.history[metric_type]
            if points is not None:
                data = data[-points:]
            
            return {metric_type: data}
        
        result = {}
        for key, data in self.history.items():
            if points is not None:
                result[key] = data[-points:]
            else:
                result[key] = data
        
        return result
    
    def _update_history(self, metrics: Dict):
        """更新历史数据"""
        self.history['cpu'].append({
            'timestamp': metrics['timestamp'],
            'value': metrics['cpu']['percent']
        })
        
        self.history['memory'].append({
            'timestamp': metrics['timestamp'],
            'value': metrics['memory']['percent']
        })
        
        self.history['disk'].append({
            'timestamp': metrics['timestamp'],
            'value': metrics['disk']['percent']
        })
        
        # 计算网络速率（与上一个点相比）
        if self.history['network']:
            last = self.history['network'][-1]
            time_diff = metrics['timestamp'] - last['timestamp']
            if time_diff > 0:
                bytes_sent_rate = (metrics['network']['bytes_sent'] - last['bytes_sent']) / time_diff
                bytes_recv_rate = (metrics['network']['bytes_recv'] - last['bytes_recv']) / time_diff
            else:
                bytes_sent_rate = 0
                bytes_recv_rate = 0
        else:
            bytes_sent_rate = 0
            bytes_recv_rate = 0
        
        self.history['network'].append({
            'timestamp': metrics['timestamp'],
            'bytes_sent': metrics['network']['bytes_sent'],
            'bytes_recv': metrics['network']['bytes_recv'],
            'bytes_sent_rate': bytes_sent_rate,
            'bytes_recv_rate': bytes_recv_rate
        })
        
        # 限制历史数据点数量
        for key in self.history:
            if len(self.history[key]) > self.max_history_points:
                self.history[key] = self.history[key][-self.max_history_points:] 