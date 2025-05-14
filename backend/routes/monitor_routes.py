from flask import Blueprint, request, jsonify
import logging
from services.monitor_service import MonitorService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建蓝图
monitor_routes = Blueprint('monitor_routes', __name__)

# 初始化服务
monitor_service = MonitorService()

@monitor_routes.route('/monitor/info', methods=['GET'])
def get_system_info():
    """获取系统基本信息"""
    try:
        info = monitor_service.get_system_info()
        return jsonify(info)
    except Exception as e:
        logger.error(f"获取系统信息错误: {e}")
        return jsonify({'error': str(e)}), 500

@monitor_routes.route('/monitor/metrics', methods=['GET'])
def get_current_metrics():
    """获取当前系统性能指标"""
    try:
        metrics = monitor_service.get_current_metrics()
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"获取性能指标错误: {e}")
        return jsonify({'error': str(e)}), 500

@monitor_routes.route('/monitor/processes', methods=['GET'])
def get_process_info():
    """获取进程信息"""
    python_only = request.args.get('python_only', 'false').lower() == 'true'
    
    try:
        processes = monitor_service.get_process_info(include_python_only=python_only)
        return jsonify(processes)
    except Exception as e:
        logger.error(f"获取进程信息错误: {e}")
        return jsonify({'error': str(e)}), 500

@monitor_routes.route('/monitor/history', methods=['GET'])
def get_history():
    """获取历史性能数据"""
    metric_type = request.args.get('type')
    points = request.args.get('points')
    
    if points:
        try:
            points = int(points)
        except ValueError:
            return jsonify({'error': 'points参数必须是整数'}), 400
    
    try:
        history = monitor_service.get_history(metric_type=metric_type, points=points)
        return jsonify(history)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"获取历史数据错误: {e}")
        return jsonify({'error': str(e)}), 500 