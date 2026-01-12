# Repository Documentation Index

This document provides an overview of all documentation available for cloning and setting up the FreightMas repository.

## 📚 Documentation Files

### 🚀 Getting Started

1. **[QUICK_START.md](QUICK_START.md)** - ⏱️ 5-minute setup
   - Fast installation for new users
   - Multiple installation options
   - Quick troubleshooting
   - Best for: First-time users wanting to get started quickly

2. **[README.md](README.md)** - 📖 Main documentation
   - Project overview
   - Prerequisites
   - Installation instructions
   - Module structure
   - Key features
   - Best for: General project information and overview

3. **[CLONING_GUIDE.md](CLONING_GUIDE.md)** - 🔧 Comprehensive setup guide
   - Detailed step-by-step instructions
   - Multiple setup scenarios
   - Production deployment
   - Docker setup
   - Troubleshooting guide
   - Best for: Detailed installation and production deployments

### 🛠️ Development & Contributing

4. **[CONTRIBUTING.md](CONTRIBUTING.md)** - 🤝 Contribution guidelines
   - Fork and clone workflow
   - Development setup
   - Coding standards
   - Pull request process
   - Best for: Contributors and developers

### 🤖 Automation

5. **[clone_freightmas.sh](clone_freightmas.sh)** - 📜 Automated setup script
   - Interactive installation
   - Development mode support
   - Automatic configuration
   - Error handling
   - Best for: Automated installations and CI/CD

## 🎯 Choose Your Path

### I'm new and want to try FreightMas quickly
→ Start with **[QUICK_START.md](QUICK_START.md)**

### I want detailed installation instructions
→ Read **[CLONING_GUIDE.md](CLONING_GUIDE.md)**

### I want to understand what FreightMas does
→ Check **[README.md](README.md)**

### I want to contribute to the project
→ Follow **[CONTRIBUTING.md](CONTRIBUTING.md)**

### I want automated installation
→ Run **`./clone_freightmas.sh`**

## 📋 Quick Reference

### Essential Commands

```bash
# Clone the repository
bench get-app https://github.com/lovechigwanda/freightmas.git

# Install on site
bench --site mysite.local install-app freightmas

# Complete setup
bench --site mysite.local migrate
bench build --app freightmas
bench restart
```

### Using the Automation Script

```bash
# Make executable (first time only)
chmod +x clone_freightmas.sh

# Run with interactive prompts
./clone_freightmas.sh

# Run with options
./clone_freightmas.sh --site mysite.local --bench-path ~/frappe-bench

# Development mode
./clone_freightmas.sh --dev --site development.local
```

## 🔗 External Resources

- **Frappe Framework**: https://frappeframework.com/docs
- **ERPNext Documentation**: https://docs.erpnext.com
- **Frappe Forum**: https://discuss.frappe.io
- **GitHub Repository**: https://github.com/lovechigwanda/freightmas

## 📞 Support

- **Issues**: https://github.com/lovechigwanda/freightmas/issues
- **Email**: info@zvomaita.co.zw
- **Documentation**: Check the files in this directory

## 📝 Document Summary

| File | Purpose | Length | Best For |
|------|---------|--------|----------|
| QUICK_START.md | Fast setup | ~190 lines | New users |
| README.md | Overview | ~265 lines | General info |
| CLONING_GUIDE.md | Detailed guide | ~510 lines | Comprehensive setup |
| CONTRIBUTING.md | Development | ~330 lines | Contributors |
| clone_freightmas.sh | Automation | ~255 lines | Automated setup |

## 🔄 Keeping Documentation Updated

When making changes to the project:

1. Update **README.md** for major features
2. Update **CLONING_GUIDE.md** for installation changes
3. Update **CONTRIBUTING.md** for workflow changes
4. Update **clone_freightmas.sh** for automation improvements
5. Keep **QUICK_START.md** simple and focused

## ✅ Documentation Checklist

Use this checklist to ensure documentation is complete:

- [x] README.md has project overview
- [x] QUICK_START.md has 5-minute setup
- [x] CLONING_GUIDE.md has comprehensive instructions
- [x] CONTRIBUTING.md has fork/PR workflow
- [x] clone_freightmas.sh has automated setup
- [x] All files are properly formatted
- [x] All commands are tested
- [x] All links work correctly
- [x] Script has proper error handling
- [x] Troubleshooting sections included

---

**Last Updated**: January 2026  
**Maintained by**: Zvomaita Technologies (Pvt) Ltd

