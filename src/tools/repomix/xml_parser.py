import re
from pathlib import Path
from typing import Dict, Any, Union, List

from core.models import RepomixResultData

class RepoMixParser:
    """
    Parser for RepoMix output files with XML-like structure and tool output.
    
    This class provides static methods to parse and process RepoMix repository analysis output,
    focusing on extracting structured information from directory structures, file contents,
    and tool outputs like the Top Files list and Pack Summary.
    """
    
    @staticmethod
    def parse(file_path: Union[str, Path]) -> RepomixResultData:
        """
        Parse a RepoMix output file into a structured dictionary.
        
        Args:
            file_path: Path to the repository analysis file
            
        Returns:
            Dictionary representation of the parsed content, or empty dict if parsing failed
        """
        try:
            result_dict = RepoMixParser._parse_custom_repo_output(file_path)
            
            return RepomixResultData.model_validate(result_dict)
        except Exception as e:
            print(f"Error parsing file {file_path}: {e}")
            return {}
    
    @staticmethod
    def get_formatted_directory_tree(file_path: Union[str, Path]) -> str:
        """
        Get a formatted directory tree from the repository analysis file.
        
        Args:
            file_path: Path to the repository analysis file
            
        Returns:
            Formatted directory tree as a string
        """
        result = RepoMixParser.parse(file_path)
        if 'directory_structure' not in result:
            return "No directory structure found"
        
        return result['directory_structure']
    
    @staticmethod
    def _parse_custom_repo_output(file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Parse the custom repository analysis output format that combines
        XML-like structure with raw code content.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            Structured dictionary representation of the file content
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Initialize result structure
        result = {}
        
        # Extract directory structure section
        dir_structure_match = re.search(
            r'<directory_structure>(.*?)</directory_structure>',
            content, 
            re.DOTALL
        )
        if dir_structure_match:
            dir_content = dir_structure_match.group(1).strip()
            result['directory_structure'] = RepoMixParser._format_simple_directory_tree(dir_content)
        
        # Extract cursor position if present
        cursor_match = re.search(r'<CURRENT_CURSOR_POSITION>', content)
        if cursor_match:
            result['cursor_position'] = cursor_match.start()
        
        # Extract instruction section if present
        instruction_match = re.search(r'<instruction>(.*?)</instruction>', content, re.DOTALL)
        if instruction_match:
            instruction_content = instruction_match.group(1).strip()
            result['instruction'] = instruction_content
        
        # Extract tool output section if present
        tool_output_match = re.search(r'<tool_output>(.*?)</tool_output>', content, re.DOTALL)
        if tool_output_match:
            tool_output_content = tool_output_match.group(1).strip()
            
            # Extract and process specific sections from tool output
            result['tool_output'] = RepoMixParser._extract_tool_output_sections(tool_output_content)
        
        # Extract files section
        files_match = re.search(r'<files>(.*?)</files>', content, re.DOTALL)
        if files_match:
            files_section = files_match.group(1).strip()
            result['files'] = RepoMixParser._parse_files_section(files_section)
        
        return result
    
    @staticmethod
    def _extract_tool_output_sections(content: str) -> Dict[str, Any]:
        """
        Extract specific sections from the tool output.
        
        Args:
            content: The tool output content
            
        Returns:
            Dictionary with structured sections from the tool output
        """
        result = {}
        
        # Extract Top Files section
        top_files_match = re.search(
            r'📈 Top 50 Files by Character Count and Token Count:.*?(?=\n\n)', 
            content, 
            re.DOTALL
        )
        if top_files_match:
            top_files_section = top_files_match.group(0)
            result['top_files'] = RepoMixParser._parse_top_files_section(top_files_section)
        
        # Extract Pack Summary section
        summary_match = re.search(
            r'📊 Pack Summary:.*?(?=\n\n)', 
            content, 
            re.DOTALL
        )
        if summary_match:
            summary_section = summary_match.group(0)
            result['summary'] = RepoMixParser._parse_summary_section(summary_section)
        
        return result
    
    @staticmethod
    def _parse_top_files_section(section: str) -> List[Dict[str, Any]]:
        """
        Parse the Top Files section into a structured format.
        
        Args:
            section: The Top Files section content
            
        Returns:
            List of dictionaries with file information
        """
        lines = section.splitlines()
        top_files = []
        
        # Skip the header lines
        for line in lines[2:]:
            line = line.strip()
            if not line:
                continue
            
            # Extract file information using regex
            match = re.match(r'(\d+)\.\s+(.*?)\s+\((\d+,?\d*)\s+chars,\s+(\d+,?\d*)\s+tokens\)', line)
            if match:
                rank = int(match.group(1))
                file_path = match.group(2)
                chars = int(match.group(3).replace(',', ''))
                tokens = int(match.group(4).replace(',', ''))
                
                top_files.append({
                    'rank': rank,
                    'path': file_path,
                    'chars': chars,
                    'tokens': tokens
                })
        
        return top_files
    
    @staticmethod
    def _parse_summary_section(section: str) -> Dict[str, Any]:
        """
        Parse the Pack Summary section into a structured format.
        
        Args:
            section: The Pack Summary section content
            
        Returns:
            Dictionary with summary information
        """
        summary = {}
        
        # Extract total files
        files_match = re.search(r'Total Files:\s+(\d+)', section)
        if files_match:
            summary['total_files'] = int(files_match.group(1))
        
        # Extract total characters
        chars_match = re.search(r'Total Chars:\s+([\d,]+)', section)
        if chars_match:
            summary['total_chars'] = int(chars_match.group(1).replace(',', ''))
        
        # Extract total tokens
        tokens_match = re.search(r'Total Tokens:\s+([\d,]+)', section)
        if tokens_match:
            summary['total_tokens'] = int(tokens_match.group(1).replace(',', ''))
        
        # Extract output file path
        output_match = re.search(r'Output:\s+(.*?)$', section, re.MULTILINE)
        if output_match:
            summary['output_file'] = output_match.group(1).strip()
        
        # Extract security status
        security_match = re.search(r'Security:\s+(.*?)$', section, re.MULTILINE)
        if security_match:
            summary['security'] = security_match.group(1).strip()
        
        return summary
    
    @staticmethod
    def _format_simple_directory_tree(content: str) -> str:
        """
        Format the directory structure with simple tree connectors.
        
        Args:
            content: Raw directory structure content
            
        Returns:
            Formatted directory structure with tree connectors
        """
        lines = content.splitlines()
        formatted_lines = []
        
        for line in lines:
            if not line.strip():
                continue
            
            # Extract leading spaces to preserve indentation
            leading_spaces = re.match(r'^(\s*)', line).group(1)
            content_part = line.lstrip()
            
            # Check if it's a directory (ends with /)
            is_dir = content_part.endswith('/')
            
            # Preserve indentation and add connector
            if is_dir:
                # Directory connector
                new_line = f"{leading_spaces}└── {content_part}"
            else:
                # File connector
                new_line = f"{leading_spaces}├── {content_part}"
                
            formatted_lines.append(new_line)
        
        return '\n'.join(formatted_lines)
    
    @staticmethod
    def _parse_files_section(content: str) -> List[Dict[str, str]]:
        """
        Parse the files section which contains file paths and their contents.
        
        Args:
            content: The content of the files section
            
        Returns:
            List of dictionaries containing file paths and contents
        """
        files = []
        
        # Extract file blocks using regex
        file_pattern = r'<file path="([^"]+)">(.*?)</file>'
        file_matches = re.finditer(file_pattern, content, re.DOTALL)
        
        for match in file_matches:
            path = match.group(1)
            file_content = match.group(2).strip()
            files.append({
                "path": path,
                "content": file_content
            })
        
        return files

__all__ = ["RepoMixParser"]

