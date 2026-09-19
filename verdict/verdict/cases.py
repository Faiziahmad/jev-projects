from __future__ import annotations

CASES = {
    "espionage": {
        "title": "The Crown v. Marcus Webb",
        "charge": "Corporate Espionage — Theft of Trade Secrets",
        "defendant": "Marcus Webb, Senior Software Engineer",
        "facts": [
            "Marcus Webb, senior engineer at TechCorp, submitted resignation on March 15",
            "48 hours before resignation: 2.4GB transferred from work laptop to personal USB drive",
            "Transferred files included unreleased product source code and internal roadmaps",
            "Webb joined direct competitor NovaSoft exactly 3 days after resignation",
            "NovaSoft launched a near-identical product 4 months later",
            "Webb claims he transferred 'personal notes and old projects he worked on'",
            "DLP logs show the transfer occurred at 11:47 PM — outside business hours",
            "Webb had signed a comprehensive NDA and IP assignment agreement",
        ],
        "evidence": [
            "DLP log showing 2.4GB transfer to USB device",
            "File manifest: 847 source files, 12 internal roadmap documents",
            "NovaSoft product comparison showing 73% code similarity (expert testimony)",
            "Webb's NDA signed at onboarding",
            "Email from NovaSoft recruiter dated 2 weeks before resignation",
            "Webb's personal statement claiming files were his own work",
        ],
    },
    "breach": {
        "title": "State v. Sarah Chen",
        "charge": "Unauthorized Computer Access and Data Theft",
        "defendant": "Sarah Chen, Former IT Administrator",
        "facts": [
            "Sarah Chen was terminated from Meridian Health on June 3rd",
            "Her access credentials were revoked at 5:00 PM on termination day",
            "At 11:23 PM that same night, someone accessed the database using her old credentials",
            "45,000 patient records were exported during a 12-minute session",
            "The login originated from a VPN exit node traced to her home ISP",
            "Chen claims her laptop was stolen the week before and she never accessed the system",
            "No police report for the alleged laptop theft was filed",
            "The exported data appeared for sale on a dark web forum 3 weeks later",
        ],
        "evidence": [
            "Server access logs showing login with Chen's credentials post-termination",
            "ISP records linking VPN session to Chen's home internet connection",
            "Dark web listing containing the stolen patient records",
            "Absence of police report for claimed laptop theft",
            "Access control records showing credentials were not properly invalidated until 11:45 PM",
            "Chen's statement claiming the laptop theft",
        ],
    },
    "fraud": {
        "title": "People v. David Okafor",
        "charge": "Wire Fraud and Social Engineering",
        "defendant": "David Okafor, Financial Advisor",
        "facts": [
            "David Okafor managed retirement portfolios for 23 elderly clients over 8 years",
            "Between 2023-2026, $2.1M was transferred from client accounts to shell companies",
            "Okafor forged client signatures on 47 transfer authorization forms",
            "Clients were told the transfers were 'tax optimization maneuvers'",
            "Three clients report Okafor told them their accounts had been hacked and transfers were 'protective'",
            "Okafor purchased a beachfront property in cash in 2024 while earning $85k salary",
            "Okafor claims all transfers were authorized and clients are confused due to age",
            "Handwriting expert confirms signature forgeries with 94% certainty",
        ],
        "evidence": [
            "Bank records showing $2.1M in unauthorized transfers",
            "Forged authorization forms with expert testimony confirming forgery",
            "Cash purchase deed for $780k beachfront property",
            "Recorded phone calls where Okafor falsely claimed accounts were hacked",
            "Shell company registration showing Okafor as beneficial owner",
            "Client testimonies from 7 affected individuals",
        ],
    },
}

DEFAULT_CASE = "espionage"
