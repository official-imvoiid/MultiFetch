# WebScap CLI

A powerful command-line image scraping tool designed for AI/ML research, dataset creation, and personal use. WebScap provides easy access to images from multiple platforms to help build comprehensive datasets for AI model training.

## 🚀 Motivation

This project was born from the challenge of finding quality datasets for AI Text-To-Video model training. WebScap solves this problem by providing a simple, efficient way to gather large image datasets from various platforms, enabling:

- **Training Data Collection**: Build robust datasets for AI model training
- **Topic Understanding**: Help AI models understand specific subjects through visual data
- **Vision Capability Enhancement**: Improve model performance by including diverse image datasets

## ✨ Features

WebScap supports scraping from 10 different platforms:

- **Pinterest** - Creative inspiration and lifestyle images
- **DeviantArt** - Digital art and creative content
- **Pixiv Art** - Japanese illustration and artwork (Requires PHPSESSID)
- **Civitai** - AI-generated art and models (Requires API)
- **Google Images** - Comprehensive web image search
- **WebScap GIF** - Specialized GIF collection and animation scraping
- **StaticPage** - Extract images from static websites and HTML pages
- **Image Upscaler** - Enhance image quality automatically
- **Image Converter** - Convert images between different formats

## 📋 Requirements

### System Requirements
- **Operating System**: Windows 11
- **Python**: Version 8+ 
- **Browser**: Google Chrome (installed and set as default)

### API Requirements
- **Pixiv**: PHPSESSID token required
- **Civitai**: API key required

## 📊 Performance

- **Tested Capacity**: Successfully scraped 1,700+ images
- **API Calls**: Handles 200+ API requests efficiently
- **GIF Support**: Optimized for animated content collection
- **Static Pages**: Efficiently extracts images from HTML/CSS structures
- **Scalability**: Potentially supports larger volumes (untested)

## 🔒 Content Policy & NSFW Handling

WebScap respects platform-specific content policies and user preferences:

### NSFW Content Management
- **Default Behavior**: Platforms maintain their original NSFW/SFW structure
- **User Control**: Content filtering depends on your platform account settings
- **Safe Mode**: Enable "Safe=ON" in your account settings to avoid NSFW content on supported platforms
- **Platform Respect**: No modification of platform content policies - choice remains with users

### Supported Platforms NSFW Policy
- ✅ **Google Images**: Follows your SafeSearch settings
- ✅ **Pinterest**: Default Safe Setting is on  
- ✅ **DeviantArt**: Default Safe Setting is on
- ✅ **Pixiv**: Follows account content filters
- ✅ **Civitai**: Respects platform content settings

## ⚠️ Important Disclaimer

**Developer Responsibility Notice**: 
The developers are not responsible for user actions. Please use this tool responsibly and ethically.

### Acceptable Use
✅ **Permitted Uses:**
- AI/ML research and development
- Academic research projects
- Personal dataset creation
- Fair use educational purposes

❌ **Prohibited Uses:**
- Commercial redistribution without permission
- Violation of platform Terms of Service
- Copyright infringement
- Malicious or harmful activities

### Legal Compliance
- Always follow platform Terms of Service
- Respect copyright and intellectual property rights
- Use scraped content within fair use guidelines
- Ensure compliance with local laws and regulations

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/official-imvoiid/MultiFetch.git

# Navigate to project directory
cd MultiFetch

# Install dependencies
pip install -r requirements.txt
```

## 🔧 Configuration

### Required Setup
1. Ensure Chrome is installed and set as default browser
2. Obtain necessary API keys/tokens:
   - **Pixiv**: Get your PHPSESSID from browser cookies
   - **Civitai**: Register and obtain API key

### Platform Account Settings
For optimal results and content filtering:
1. Configure your account settings on each platform
2. Set appropriate content filters (Safe=ON for family-friendly content)
3. Adjust privacy and content preferences as needed

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Remember**: Always scrape responsibly and ethically. Respect platform terms of service and copyright laws.
