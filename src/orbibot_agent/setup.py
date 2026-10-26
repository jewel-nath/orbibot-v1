from setuptools import find_packages, setup

package_name = 'orbibot_agent'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/chat_server.launch.py',
                                                  'launch/mcp_server.launch.py']),
        ('share/' + package_name + '/config', ['config/agent_params.yaml',
                                                  'config/system_prompt.txt']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Jewel Nath',
    maintainer_email='58494211+jewel-nath@users.noreply.github.com',
    description='Unified AI agent for OrbiBot - Multi-LLM support with Web GUI, Terminal, and MCP interfaces',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'chat_server = orbibot_agent.interfaces.chat_server:main',
            'chat_cli = orbibot_agent.interfaces.chat_cli:main',
            'mcp_server = orbibot_agent.interfaces.mcp_server:main',
            'agent_node = orbibot_agent.agent_node:main',
        ],
    },
)