import React from "react";
import { useState, useEffect } from "react";
import { Navigate, useNavigate } from 'react-router-dom';
import './UserLogin.css'

const UserLogin = () => {
    const [user, setUser] = useState(null);
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [isValid, setIsValid] = useState(true);
    const [loginAttempts, setLoginAttempts] = useState(0);
    const [loginError, setLoginError] = useState("");
    const [passwordError, setPasswordError] = useState("");
    const [isLocked, setIsLocked] = useState(false);
    const [remainingTime, setRemainingTime] = useState(0);
    const navigate = useNavigate();

    useEffect(() => {
        if(user) {
            console.log(`User logged in at frontend: ${user}`);
            navigate('/FitnessApp');
        }
    }, [user]);

    useEffect(() => {
        const storedAttempts = parseInt(localStorage.getItem("loginAttempts")) || 0;
        const lockTime = parseInt(localStorage.getItem("lockTime")) || 0;
        const currentTime = Date.now();

        if(storedAttempts >= 5 && currentTime < lockTime) {
            setIsLocked(true);
            setRemainingTime(Math.ceil((lockTime - currentTime) / 1000));
            startTimer(lockTime - currentTime);
        }
    }, []);

    const startTimer = (duration) => {
        const interval = setInterval(() => {
            const currentTime = Date.now();
            const lockTime = parseInt(localStorage.getItem("lockTime")) || 0;

            if(currentTime >= lockTime) {
                clearInterval(interval);
                setIsLocked(false);
                setLoginAttempts(0);
                localStorage.removeItem("loginAttempts");
                localStorage.removeItem("lockTime");
            } else {
                setRemainingTime(Math.ceil((lockTime - currentTime) / 1000));
            }
        }, 1000);
    };

    function validatePassword(password) {
        const regex = /^(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$/; // Ensure at least 8 characters and 1 special character
        return regex.test(password);
    };

    const handleLogin = async (event) => {
        event.preventDefault();
        setLoginError("");
        setPasswordError("");
        if(isLocked) {
            setLoginError(`Too many login attempts. Try again in ${remainingTime} seconds.`);
            return;
        }

        if(!validatePassword(password)) {
            setPasswordError("Password must be at least 8 characters long and contain at least one special character.");
            return;
        }
        if(loginAttempts > 5) {
            alert("Too many login attempts, please try again later.");
            return;
        }
        setLoginAttempts(prevAttempts => prevAttempts + 1);
        if(!username || !password) {
            console.error("No username or password selected.");
        }
        //TODO: need to find a way to search in django postgres database for 
        //valid password or username, else notify them they entered wrong login credentials
        //or they need to make a new account
        try {
            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);
            const response = await fetch(`${process.env.REACT_APP_API_URL}/api/login/`, {
                method: 'POST',
                body: formData,
            });
            if(!response.ok) {
                throw new Error(`HTTP error! status ${response.status}`);
            }
            const validUser = await response.json();
            if(!validUser) {
                throw new Error("No user returned from the backend.");
            } else {
                console.log("Valid User: ", validUser);

                localStorage.setItem('token', validUser.token);
                localStorage.setItem('user_id', validUser.user_id);
                localStorage.setItem('username', validUser.username)

                setUser(validUser.exists);
            }
        } catch(error) {
            console.error("Error logging in:", error);
            setLoginError("User not found in system. Please try another username or password or create a new account below.");
        } finally {
            setLoginAttempts(0);
        }

    };

    const handleNewUserClick = () => {
        navigate("/NewUser");
    };

    return (
        <div className="userlogin-container">
            <h1 className="userlogin-title">Welcome to Fitness AI App</h1>
            <form className="userlogin-form" onSubmit={handleLogin}>
                <label>Username: <input className="username-input" type="text" onChange={(e) => setUsername(e.target.value)} required/></label>
                <label>Password: 
                    <input className="password-input" type="password" value={password}
                    onChange={(e) => {
                        setPassword(e.target.value);
                        setIsValid(validatePassword(e.target.value));
                    }}
                    required/>
                </label>
                <button className="login-button" type="submit" disabled={isLocked}>Login</button>
            </form>
            {passwordError && <p className="error-message">{passwordError}</p>}
            {loginError && <p className="error-message">{loginError}</p>}
            <button className="newuser-button" onClick={handleNewUserClick}>Create New Account</button>
        </div>
    );
};

export default UserLogin;