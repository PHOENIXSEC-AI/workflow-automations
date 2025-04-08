"""
Models for extracting and structuring security analysis data from agent results.

This module defines Pydantic models to capture security-related information
extracted during code security reviews, including vulnerabilities, sensitive data,
and security recommendations.
"""
from typing import List, Optional, Self
from pydantic import BaseModel, Field

from .base import AgentAnalysisResult

# Malicious Code Elements
class MaliciousCodeElement(BaseModel):
    """
    Information about potentially malicious code detected in the codebase.
    
    Captures details about backdoors, hardcoded credentials, suspicious 
    connections or functionality that might indicate malicious intent.
    """
    type: str = Field(description="Type of malicious element (backdoor, hardcoded credential, etc.)")
    description: str = Field(description="Description of the potential malicious code")
    location: str = Field(description="File path and line numbers where this was found")
    severity: str = Field(description="Severity rating (Critical, High, Medium, Low, Info)")
    confidence: str = Field(description="Confidence level in the finding (High, Medium, Low)")
    false_positive_likelihood: Optional[str] = Field(None, description="Likelihood this is a false positive (Low, Medium, High)")
    false_positive_reasoning: Optional[str] = Field(None, description="Reasoning for why this might be a false positive")

# Sensitive Information
class SensitiveInfoElement(BaseModel):
    """
    Information about sensitive data exposure detected in the codebase.
    
    Captures details about exposed secrets, PII, or other sensitive information
    that should be properly secured.
    """
    type: str = Field(description="Type of sensitive information (secret, token, PII, etc.)")
    description: str = Field(description="Description of the sensitive information")
    location: str = Field(description="File path and line numbers where this was found")
    severity: str = Field(description="Severity rating (Critical, High, Medium, Low, Info)")
    data_classification: Optional[str] = Field(None, description="Classification of the sensitive data (if applicable)")
    false_positive_likelihood: Optional[str] = Field(None, description="Likelihood this is a false positive (Low, Medium, High)")
    false_positive_reasoning: Optional[str] = Field(None, description="Reasoning for why this might be a false positive")

# OWASP ASVS Vulnerabilities
class VulnerabilityElement(BaseModel):
    """
    Information about security vulnerabilities detected in the codebase.
    
    Captures details about various types of vulnerabilities based on 
    OWASP ASVS categories.
    """
    category: str = Field(description="OWASP ASVS category (Authentication, Access Control, etc.)")
    vulnerability_type: str = Field(description="Specific vulnerability type (SQL Injection, XSS, etc.)")
    description: str = Field(description="Description of the vulnerability")
    location: str = Field(description="File path and line numbers where this was found")
    severity: str = Field(description="Severity rating (Critical, High, Medium, Low, Info)")
    cwe_id: Optional[str] = Field(None, description="Common Weakness Enumeration ID if applicable")
    false_positive_likelihood: Optional[str] = Field(None, description="Likelihood this is a false positive (Low, Medium, High)")
    false_positive_reasoning: Optional[str] = Field(None, description="Reasoning for why this might be a false positive")

# Security Recommendations
class SecurityRecommendation(BaseModel):
    """
    Remediation recommendations for identified security issues.
    
    Captures actionable recommendations to address security vulnerabilities
    and improve the overall security posture.
    """
    issue_reference: str = Field(description="Reference to the related vulnerability or issue")
    recommendation: str = Field(description="Detailed recommendation on how to fix the issue")
    priority: str = Field(description="Priority for implementing this fix (High, Medium, Low)")
    code_example: Optional[str] = Field(None, description="Example code showing how to implement the fix")
    asvs_reference: Optional[str] = Field(None, description="Relevant OWASP ASVS requirement reference")

# Concrete SecurityAnalysisResult with expected fields
class SecurityAnalysisResult(AgentAnalysisResult):
    """
    Structured result from security analysis with specific expected fields.
    
    Extends the base AgentAnalysisResult to include structured data about
    malicious code elements, sensitive information exposure, vulnerabilities,
    and security recommendations identified during code security review.
    """
    malicious_elements: List[MaliciousCodeElement] = Field(default_factory=list, description="Potentially malicious code elements detected")
    sensitive_info: List[SensitiveInfoElement] = Field(default_factory=list, description="Sensitive information exposure detected")
    vulnerabilities: List[VulnerabilityElement] = Field(default_factory=list, description="Security vulnerabilities detected")
    recommendations: List[SecurityRecommendation] = Field(default_factory=list, description="Security recommendations")
    overall_risk_score: int = Field(0, description="Overall security risk score (0-100, higher is riskier)")
    score_justification: str = Field("", description="Brief justification for the assigned risk score")
    
    @staticmethod
    def default() -> Self:
        """
        Creates a default instance with default values.
        
        Returns:
            A new SecurityAnalysisResult instance with default values
        """
        return SecurityAnalysisResult(file_path='default')

__all__ = [
    "MaliciousCodeElement",
    "SensitiveInfoElement",
    "VulnerabilityElement",
    "SecurityRecommendation",
    "SecurityAnalysisResult"
] 