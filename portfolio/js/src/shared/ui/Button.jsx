const variants = {
  primary: "btn-primary",
  secondary: "btn-secondary",
  outline: "btn-outline",
};

const Button = ({
  variant = "primary",
  type = "button",
  className = "",
  ...props
}) => (
  <button
    type={type}
    className={`${variants[variant]} ${className}`.trim()}
    {...props}
  />
);

export default Button;
